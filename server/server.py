import socket
import threading
from database import init_db, add_user, authenticate_user, set_driver_profile, add_schedule, get_drivers_in_area_time, save_ride, add_rating
from protocol import recv_json, send_json
import hashlib

HOST = '0.0.0.0'
PORT = 5555
clients = {}      # username -> (conn, addr)
db_lock = threading.Lock()


# -----------------------------
# Utility: password hashing
# -----------------------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


# -----------------------------
# Client Handlers
# -----------------------------
def handle_register(conn, p):
    name = p["name"]
    email = p["email"]
    username = p["username"]
    password = hash_password(p["password"])
    with db_lock:
        success = add_user(name, email, username, password)
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
        return username
    else:
        send_json(conn, {"type": "LOGIN_FAIL"})
        return None


def handle_set_driver(conn, p):
    with db_lock:
        set_driver_profile(p["user_id"], p["is_driver"], p["area"])
    send_json(conn, {"type": "SET_DRIVER_OK"})


def handle_add_schedule(conn, p):
    with db_lock:
        add_schedule(p["user_id"], p["day"], p["time"], p["direction"])
    send_json(conn, {"type": "ADD_SCHEDULE_OK"})


def handle_request_ride(conn, p):
    with db_lock:
        drivers = get_drivers_in_area_time(p["area"], p["day"], p["time"], p.get("min_rating", 0))
    send_json(conn, {"type": "DRIVER_LIST", "payload": {"drivers": drivers}})


def handle_driver_response(conn, p):
    passenger_username = p["passenger_username"]
    if passenger_username in clients:
        passenger_conn, _ = clients[passenger_username]
        send_json(passenger_conn, {"type": "DRIVER_RESPONSE", "payload": p})
    send_json(conn, {"type": "DRIVER_RESPONSE_OK"})


def handle_add_rating(conn, p):
    with db_lock:
        add_rating(p["rated_user_id"], p["rater_user_id"], p["rating"], p["role"], p.get("ride_id"))
    send_json(conn, {"type": "ADD_RATING_OK"})


def handle_client(conn, addr):
    username = None
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
                username = handle_login(conn, p)
                if username:
                    clients[username] = (conn, addr)
            elif t == "SET_DRIVER":
                handle_set_driver(conn, p)
            elif t == "ADD_SCHEDULE":
                handle_add_schedule(conn, p)
            elif t == "REQUEST_RIDE":
                handle_request_ride(conn, p)
            elif t == "DRIVER_RESPONSE":
                handle_driver_response(conn, p)
            elif t == "ADD_RATING":
                handle_add_rating(conn, p)
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
    start_server()
