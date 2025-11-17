import socket
import threading
import hashlib
import argparse
import sys
from datetime import datetime, timedelta

from database import (
    init_db,
    add_user,
    authenticate_user,
    set_user_role,
    add_schedule,
    get_schedule_entries,
    delete_schedule_entry,
    delete_schedule_for_user,
    find_drivers,
    create_ride_request,
    accept_ride_request,
    get_ride_requests_for_driver,
    save_ride,
    start_ride,
    complete_ride,
    get_user_rides,
    upsert_rating,
    get_user_by_username,
    get_user_by_id,
    get_pending_rides_for_driver,
    save_message,
    fetch_messages,
    list_contacts,
    get_ride_by_id,
    update_ride_status,
    get_average_rating,
)
from protocol import recv_json, send_json

HOST = '0.0.0.0'
PORT = 5555
clients = {}      # username -> {"conn": socket, "addr": addr, "user_id": int, "peer": {"ip": str, "port": int}}
db_lock = threading.Lock()
RATING_WINDOW = timedelta(hours=36)


# -----------------------------
# Utility helpers
# -----------------------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def send_to_username(username, data):
    client = clients.get(username)
    if client:
        send_json(client["conn"], data)


def can_edit_rating(ride):
    if not ride or not ride.get("completed_at"):
        return False
    completed = datetime.fromisoformat(ride["completed_at"])
    return datetime.utcnow() - completed <= RATING_WINDOW


# -----------------------------
# Client Handlers
# -----------------------------
def handle_register(conn, p):
    name = p["name"]
    email = p["email"]
    username = p["username"]
    password = hash_password(p["password"])
    role = p["role"]
    area = p.get("area")
    schedule = p.get("schedule")
    with db_lock:
        success = add_user(name, email, username, password, role, area, schedule)
    if success:
        send_json(conn, {"type": "REGISTER_OK"})
    else:
        send_json(conn, {"type": "REGISTER_FAIL", "payload": {"reason": "Username taken"}})


def handle_login(conn, p):
    username = p["username"]
    password = hash_password(p["password"])
    with db_lock:
        user = authenticate_user(username, password)
    if user:
        send_json(conn, {"type": "LOGIN_OK", "payload": user})
        return username, user["user_id"]
    else:
        send_json(conn, {"type": "LOGIN_FAIL"})
        return None, None


def handle_announce_peer(conn, p, username, addr):
    """Record a client's peer listening port (for P2P)."""
    if not username:
        send_json(conn, {"type": "ANNOUNCE_FAIL", "payload": {"reason": "Not authenticated"}})
        return
    port = p.get("port")
    if not port:
        send_json(conn, {"type": "ANNOUNCE_FAIL", "payload": {"reason": "port missing"}})
        return
    # store peer info for username
    info = clients.get(username, {})
    info["peer"] = {"ip": addr[0], "port": int(port)}
    clients[username] = info
    try:
        print(f"[Server] ANNOUNCE_PEER from {username} at {addr[0]}:{port}")
    except Exception:
        pass
    send_json(conn, {"type": "ANNOUNCE_OK"})


def handle_set_role(conn, p):
    user_id = p["user_id"]
    role = p["role"]
    area = p.get("area")
    min_rating = p.get("min_rating")
    with db_lock:
        current = get_user_by_id(user_id)
        # Prevent downgrading an existing driver to passenger
        if current and current.get("is_driver") and role != "driver":
            send_json(conn, {"type": "SET_ROLE_FAIL", "payload": {"reason": "Cannot change from driver to passenger"}})
            return
        # Allow upgrades (passenger -> driver) and updates to role/area
        set_user_role(user_id, role, area, min_rating=min_rating)
    send_json(conn, {"type": "SET_ROLE_OK"})


def handle_add_schedule(conn, p):
    with db_lock:
        add_schedule(p["user_id"], p["day"], p["time"], p["direction"], p.get("area"))
    send_json(conn, {"type": "ADD_SCHEDULE_OK"})


def handle_list_schedule(conn, p):
    with db_lock:
        entries = get_schedule_entries(p["user_id"])
    send_json(conn, {"type": "SCHEDULE_LIST", "payload": {"entries": entries}})


def handle_delete_schedule(conn, p):
    with db_lock:
        delete_schedule_entry(p["schedule_id"], p["user_id"])
    send_json(conn, {"type": "DELETE_SCHEDULE_OK"})


def handle_broadcast_ride_request(conn, p):
    passenger_id = p["passenger_id"]
    direction = p["direction"]
    day = p["day"]
    time = p["time"]
    area = p["area"] # Extract area from payload
    with db_lock:
        # Enforce passenger's minimum-driver-rating preference and drivers' minimum-passenger-rating preference.
        passenger = get_user_by_id(passenger_id)
        passenger_min = passenger.get("min_rating", 0) if passenger else 0
        passenger_avg = get_average_rating(passenger_id, 'passenger') if passenger else 0

        # Find drivers whose average driver rating >= passenger's preferred minimum
        drivers = find_drivers(direction, day, time, area, min_rating=passenger_min)
        if not drivers:
            send_json(conn, {"type": "NO_DRIVERS_FOUND"})
            return

        # Filter out drivers who have set a min_rating higher than the passenger's average rating
        eligible_drivers = []
        for d in drivers:
            drv_user = get_user_by_id(d["id"])
            drv_min = drv_user.get("min_rating", 0) if drv_user else 0
            if passenger_avg >= drv_min:
                eligible_drivers.append(d)

        if not eligible_drivers:
            # No drivers meet both sides' minimum-rating constraints
            send_json(conn, {"type": "NO_DRIVERS_FOUND"})
            return

        driver_ids = [driver["id"] for driver in eligible_drivers]
        ride_id = create_ride_request(passenger_id, direction, day, time, area, driver_ids)

        for driver in eligible_drivers:
            send_to_username(driver["username"], {
                "type": "RIDE_REQUEST",
                "payload": {
                    "ride_id": ride_id,
                    "passenger_id": passenger_id,
                    "passenger_name": passenger["name"] if passenger else "Unknown",
                    "direction": direction,
                    "time": time,
                }
            })
    send_json(conn, {"type": "BROADCAST_OK", "payload": {"ride_id": ride_id}})


def handle_fetch_pending(conn, p):
    driver_id = p["driver_id"]
    with db_lock:
        pending = get_pending_rides_for_driver(driver_id)
    send_json(conn, {"type": "PENDING_RIDES", "payload": {"rides": pending}})


def handle_fetch_ride_requests(conn, p):
    driver_id = p["driver_id"]
    with db_lock:
        requests = get_ride_requests_for_driver(driver_id)
    send_json(conn, {"type": "RIDE_REQUEST_LIST", "payload": {"requests": requests}})


def handle_driver_response(conn, p):
    # validate payload fields and try to infer missing driver_id from the connection
    ride_id = p.get("ride_id")
    status = p.get("status")
    driver_id = p.get("driver_id")

    if ride_id is None or status is None:
        send_json(conn, {"type": "DRIVER_RESPONSE_OK", "payload": {"status": "ERROR", "reason": "missing ride_id or status"}})
        return

    # If driver_id not provided by client, try to infer it from the connection's registered username
    if driver_id is None:
        inferred = None
        for uname, info in clients.items():
            if info.get("conn") is conn:
                inferred = info.get("user_id")
                break
        if inferred is not None:
            driver_id = inferred
        else:
            send_json(conn, {"type": "DRIVER_RESPONSE_OK", "payload": {"status": "ERROR", "reason": "driver_id missing and could not be inferred"}})
            return
    with db_lock:
        ride = get_ride_by_id(ride_id)
        if not ride or ride["status"] != "PENDING":
            # Ride already taken or cancelled
            send_json(conn, {"type": "DRIVER_RESPONSE_OK", "payload": {"status": "CLOSED"}})
            return

        if status == "ACCEPTED":
            other_driver_ids = accept_ride_request(ride_id, driver_id)
            passenger = get_user_by_id(ride["passenger_id"])
            # Include driver's peer IP/port in the notification when available
            driver_user = get_user_by_id(driver_id)
            peer_info = None
            if driver_user:
                info = clients.get(driver_user.get('username'), {})
                peer_info = info.get('peer') if info else None
            payload = {"ride_id": ride_id, "status": "ACCEPTED"}
            if peer_info:
                payload["driver_ip"] = peer_info.get("ip")
                payload["driver_port"] = peer_info.get("port")
            if driver_user:
                payload["driver_username"] = driver_user.get("username")
            if passenger:
                send_to_username(passenger["username"], {"type": "DRIVER_RESPONSE", "payload": payload})

            for other_driver_id in other_driver_ids:
                other_driver = get_user_by_id(other_driver_id)
                if other_driver:
                    send_to_username(other_driver["username"], {"type": "RIDE_UNAVAILABLE", "payload": {"ride_id": ride_id}})
            send_json(conn, {"type": "DRIVER_RESPONSE_OK", "payload": {"status": "ACCEPTED"}})
        else: # DENIED
            # We just notify the passenger that one of the drivers denied.
            # The request is still open to other drivers.
            passenger = get_user_by_id(ride["passenger_id"])
            if passenger:
                send_to_username(passenger["username"], {"type": "DRIVER_RESPONSE", "payload": {"ride_id": ride_id, "status": "DENIED"}})
            send_json(conn, {"type": "DRIVER_RESPONSE_OK", "payload": {"status": "DENIED"}})


def handle_fetch_rides(conn, p):
    user_id = p["user_id"]
    with db_lock:
        rides = get_user_rides(user_id)
    send_json(conn, {"type": "RIDES_LIST", "payload": {"rides": rides}})


def handle_update_rating(conn, p):
    ride_id = p["ride_id"]
    rater_id = p["rater_user_id"]
    rating = p["rating"]
    with db_lock:
        ride = get_ride_by_id(ride_id)
        if not ride:
            send_json(conn, {"type": "UPDATE_RATING_FAIL", "payload": {"reason": "Ride not found"}})
            return
        if rater_id not in (ride["passenger_id"], ride["driver_id"]):
            send_json(conn, {"type": "UPDATE_RATING_FAIL", "payload": {"reason": "Not part of this ride"}})
            return
        if not can_edit_rating(ride):
            send_json(conn, {"type": "UPDATE_RATING_FAIL", "payload": {"reason": "Rating window closed"}})
            return
        if rater_id == ride["passenger_id"]:
            rated_user_id = ride["driver_id"]
            role = "driver"
        else:
            rated_user_id = ride["passenger_id"]
            role = "passenger"
        upsert_rating(rated_user_id, rater_id, rating, role, ride_id)
    send_json(conn, {"type": "UPDATE_RATING_OK"})


def handle_start_ride(conn, p):
    ride_id = p["ride_id"]
    with db_lock:
        start_ride(ride_id)
        ride = get_ride_by_id(ride_id)
        if ride:
            passenger = get_user_by_id(ride.get("passenger_id"))
            driver = get_user_by_id(ride.get("driver_id"))
            if passenger:
                send_to_username(passenger["username"], {"type": "RIDE_STARTED", "payload": {"ride_id": ride_id}})
            if driver:
                send_to_username(driver["username"], {"type": "RIDE_STARTED", "payload": {"ride_id": ride_id}})
    send_json(conn, {"type": "START_RIDE_OK"})


def handle_complete_ride(conn, p):
    ride_id = p["ride_id"]
    with db_lock:
        complete_ride(ride_id)
        ride = get_ride_by_id(ride_id)
        if ride:
            passenger = get_user_by_id(ride.get("passenger_id"))
            driver = get_user_by_id(ride.get("driver_id"))
            if passenger:
                send_to_username(passenger["username"], {"type": "RIDE_COMPLETED", "payload": {"ride_id": ride_id}})
            if driver:
                send_to_username(driver["username"], {"type": "RIDE_COMPLETED", "payload": {"ride_id": ride_id}})
    send_json(conn, {"type": "COMPLETE_RIDE_OK"})


def handle_cancel_ride(conn, p):
    """
    Cancel a ride (passenger leaves before start, or driver removes passenger).
    Notifies the other party when possible.
    """
    ride_id = p.get("ride_id")
    if ride_id is None:
        send_json(conn, {"type": "CANCEL_RIDE_FAIL", "payload": {"reason": "ride_id missing"}})
        return
    with db_lock:
        ride = get_ride_by_id(ride_id)
        if not ride:
            send_json(conn, {"type": "CANCEL_RIDE_FAIL", "payload": {"reason": "ride not found"}})
            return
        # Only allow cancelling if ride hasn't completed
        if ride.get("status") == "COMPLETED":
            send_json(conn, {"type": "CANCEL_RIDE_FAIL", "payload": {"reason": "ride already completed"}})
            return
        update_ride_status(ride_id, "CANCELLED")
        # notify counterpart if connected
        passenger = get_user_by_id(ride.get("passenger_id"))
        driver = get_user_by_id(ride.get("driver_id"))
        if passenger and driver:
            # notify both
            send_to_username(passenger["username"], {"type": "RIDE_CANCELLED", "payload": {"ride_id": ride_id}})
            send_to_username(driver["username"], {"type": "RIDE_CANCELLED", "payload": {"ride_id": ride_id}})
        elif passenger:
            send_to_username(passenger["username"], {"type": "RIDE_CANCELLED", "payload": {"ride_id": ride_id}})
        elif driver:
            send_to_username(driver["username"], {"type": "RIDE_CANCELLED", "payload": {"ride_id": ride_id}})
    send_json(conn, {"type": "CANCEL_RIDE_OK"})


def handle_list_contacts(conn, p):
    user_id = p["user_id"]
    with db_lock:
        contacts = list_contacts(user_id)
    send_json(conn, {"type": "CONTACTS", "payload": {"contacts": contacts}})


def handle_fetch_messages(conn, p):
    user_id = p["user_id"]
    partner_id = p["partner_id"]
    with db_lock:
        messages = fetch_messages(user_id, partner_id)
    send_json(conn, {"type": "MESSAGES", "payload": {"messages": messages}})


def handle_send_message(conn, p, sender_username):
    to_username = p["to"]
    message = p["message"]
    if not sender_username:
        send_json(conn, {"type": "SEND_MESSAGE_FAIL", "payload": {"reason": "Not authenticated"}})
        return
    with db_lock:
        sender = get_user_by_username(sender_username)
        receiver = get_user_by_username(to_username)
        if not sender or not receiver:
            send_json(conn, {"type": "SEND_MESSAGE_FAIL", "payload": {"reason": "User not found"}})
            return
        msg = save_message(sender["id"], receiver["id"], message)
    send_json(conn, {"type": "SEND_MESSAGE_OK", "payload": msg})
    send_to_username(to_username, {"type": "CHAT_MESSAGE", "payload": {
        "from": sender_username,
        "from_id": sender["id"],
        "to_id": receiver["id"],
        "message": message,
        "sent_at": msg["sent_at"]
    }})


def handle_client(conn, addr):
    username = None
    user_id = None
    try:
        while True:
            msg = recv_json(conn)
            if not msg:
                break
            t = msg.get("type")
            p = msg.get("payload", {})

            if t == "REGISTER":
                handle_register(conn, p)
            elif t == "LOGIN":
                username, user_id = handle_login(conn, p)
                if username:
                    clients[username] = {"conn": conn, "addr": addr, "user_id": user_id}
            elif t == "SET_ROLE":
                handle_set_role(conn, p)
            elif t == "ADD_SCHEDULE":
                handle_add_schedule(conn, p)
            elif t == "LIST_SCHEDULE":
                handle_list_schedule(conn, p)
            elif t == "DELETE_SCHEDULE":
                handle_delete_schedule(conn, p)
            elif t == "BROADCAST_RIDE_REQUEST":
                handle_broadcast_ride_request(conn, p)
            elif t == "FETCH_RIDE_REQUESTS":
                handle_fetch_ride_requests(conn, p)
            elif t == "FETCH_PENDING":
                handle_fetch_pending(conn, p)
            elif t == "DRIVER_RESPONSE":
                handle_driver_response(conn, p)
            elif t == "ANNOUNCE_PEER":
                handle_announce_peer(conn, p, username, addr)
            elif t == "FETCH_RIDES":
                handle_fetch_rides(conn, p)
            elif t == "CANCEL_RIDE":
                handle_cancel_ride(conn, p)
            elif t == "UPDATE_RATING":
                handle_update_rating(conn, p)
            elif t == "START_RIDE":
                handle_start_ride(conn, p)
            elif t == "COMPLETE_RIDE":
                handle_complete_ride(conn, p)
            elif t == "LIST_CONTACTS":
                handle_list_contacts(conn, p)
            elif t == "FETCH_MESSAGES":
                handle_fetch_messages(conn, p)
            elif t == "SEND_MESSAGE":
                handle_send_message(conn, p, username)
            else:
                send_json(conn, {"type": "ERROR", "payload": {"message": "Unknown type"}})
    finally:
        if username in clients:
            del clients[username]
        conn.close()


# -----------------------------
# Server Main
# -----------------------------
def start_server():
    init_db()  # initialize database
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen(10)
    print(f"[+] Server running on {HOST}:{PORT}")
    while True:
        conn, addr = s.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AUBus server")
    parser.add_argument("--port", type=int, help="Port to listen on", default=5555)
    parser.add_argument("--host", type=str, help="Host to bind to", default='0.0.0.0')
    args = parser.parse_args()
    PORT = args.port
    HOST = args.host
    start_server()
