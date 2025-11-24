"""Persistent TCP API client for communicating with the AUBus server.

Handles connection, request/response waiting and asynchronous server events.
"""

import json
import socket
import threading
from dataclasses import dataclass
from queue import Queue, Empty
from typing import Any, Dict, Iterable, List, Optional, Set

from server.protocol import send_json, recv_json


class ApiClientError(Exception):
    """Raised when the frontend cannot communicate with the backend server."""


@dataclass
class ApiEvent:
    type: str
    payload: Dict[str, Any]


class ApiClient:
    """Persistent TCP client that communicates with the AUBus server."""

    def __init__(self, host: str = "127.0.0.1", port: int = 5555, timeout: float = 5.0) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout

        self._sock: Optional[socket.socket] = None
        self._receiver: Optional[threading.Thread] = None
        self._send_lock = threading.Lock()
        self._wait_lock = threading.Lock()
        self._wait_types: Set[str] = set()
        self._wait_response: Optional[Dict[str, Any]] = None
        self._wait_event = threading.Event()
        self._async_events: "Queue[Dict[str, Any]]" = Queue()
        self.username: Optional[str] = None
        self.user_id: Optional[int] = None
        self._connected = False

    # -----------------------------
    # Connection management
    # -----------------------------
    def connect(self) -> None:
        if self._connected:
            return
        sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
        sock.settimeout(None)
        self._sock = sock
        self._connected = True
        self._receiver = threading.Thread(target=self._recv_loop, daemon=True)
        self._receiver.start()

    def disconnect(self) -> None:
        self._connected = False
        if self._sock:
            try:
                self._sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self._sock.close()
        self._sock = None

    # -----------------------------
    # Public API
    # -----------------------------
    def register(self, name: str, email: str, username: str, password: str, role: str, area: Optional[str] = None, schedule: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = {"name": name, "email": email, "username": username, "password": password, "role": role}
        if area:
            payload["area"] = area
        if schedule:
            payload["schedule"] = schedule
        return self._send_once("REGISTER", payload)

    def announce_peer(self, port: int) -> Dict[str, Any]:
        """Tell the server which local TCP port this client listens on for P2P chat."""
        try:
            return self._send_and_wait("ANNOUNCE_PEER", {"port": port}, expected={"ANNOUNCE_OK", "ANNOUNCE_FAIL"})
        except ApiClientError:
            # best effort; return failure dict
            return {"type": "ANNOUNCE_FAIL", "payload": {"reason": "could not announce"}}

    def login(self, username: str, password: str) -> Dict[str, Any]:
        self.connect()
        resp = self._send_and_wait("LOGIN", {"username": username, "password": password}, expected={"LOGIN_OK", "LOGIN_FAIL"})
        if resp["type"] == "LOGIN_OK":
            payload = resp.get("payload") or {}
            self.username = username
            self.user_id = payload.get("user_id")
        return resp

    def set_role(self, user_id: int, role: str, area: Optional[str], min_rating: Optional[int] = None) -> Dict[str, Any]:
        payload = {"user_id": user_id, "role": role, "area": area}
        if min_rating is not None:
            payload["min_rating"] = int(min_rating)
        return self._send_and_wait("SET_ROLE", payload, expected={"SET_ROLE_OK"})

    def add_schedule(self, user_id: int, day: str, time: str, direction: str, area: str) -> Dict[str, Any]:
        return self._send_and_wait("ADD_SCHEDULE", {"user_id": user_id, "day": day, "time": time, "direction": direction, "area": area}, expected={"ADD_SCHEDULE_OK"})

    def list_schedule(self, user_id: int) -> Dict[str, Any]:
        return self._send_and_wait("LIST_SCHEDULE", {"user_id": user_id}, expected={"SCHEDULE_LIST"})

    def delete_schedule_entry(self, user_id: int, schedule_id: int) -> Dict[str, Any]:
        return self._send_and_wait("DELETE_SCHEDULE", {"user_id": user_id, "schedule_id": schedule_id}, expected={"DELETE_SCHEDULE_OK"})

    def broadcast_ride_request(self, passenger_id: int, direction: str, day: str, time: str, area: str) -> Dict[str, Any]:
        return self._send_and_wait("BROADCAST_RIDE_REQUEST", {"passenger_id": passenger_id, "direction": direction, "day": day, "time": time, "area": area}, expected={"BROADCAST_OK", "NO_DRIVERS_FOUND"})

    def request_drivers(self, area: str, day: str, time: str, min_rating: int = 0) -> Dict[str, Any]:
        return self._send_and_wait("REQUEST_RIDE", {"area": area, "day": day, "time": time, "min_rating": min_rating}, expected={"DRIVER_LIST"})

    def create_ride(self, passenger_id: int, driver_id: int, day: str, time: str, area: str) -> Dict[str, Any]:
        return self._send_and_wait("CREATE_RIDE", {
            "passenger_id": passenger_id,
            "driver_id": driver_id,
            "day": day,
            "time": time,
            "area": area
        }, expected={"RIDE_CREATED"})

    def fetch_pending_rides(self, driver_id: int) -> Dict[str, Any]:
        return self._send_and_wait("FETCH_PENDING", {"driver_id": driver_id}, expected={"PENDING_RIDES"})

    def fetch_ride_requests(self, driver_id: int) -> Dict[str, Any]:
        return self._send_and_wait("FETCH_RIDE_REQUESTS", {"driver_id": driver_id}, expected={"RIDE_REQUEST_LIST"})

    def respond_to_ride(self, ride_id: int, status: str) -> Dict[str, Any]:
        return self._send_and_wait("DRIVER_RESPONSE", {"ride_id": ride_id, "status": status}, expected={"DRIVER_RESPONSE_OK"})

    def fetch_rides(self, user_id: int) -> Dict[str, Any]:
        return self._send_and_wait("FETCH_RIDES", {"user_id": user_id}, expected={"RIDES_LIST"})

    def update_rating(self, ride_id: int, rater_user_id: int, rating: int) -> Dict[str, Any]:
        return self._send_and_wait("UPDATE_RATING", {
            "ride_id": ride_id,
            "rater_user_id": rater_user_id,
            "rating": rating
        }, expected={"UPDATE_RATING_OK", "UPDATE_RATING_FAIL"})

    def start_ride(self, ride_id: int) -> Dict[str, Any]:
        return self._send_and_wait("START_RIDE", {"ride_id": ride_id}, expected={"START_RIDE_OK"})

    def complete_ride(self, ride_id: int) -> Dict[str, Any]:
        return self._send_and_wait("COMPLETE_RIDE", {"ride_id": ride_id}, expected={"COMPLETE_RIDE_OK"})

    def cancel_ride(self, ride_id: int) -> Dict[str, Any]:
        return self._send_and_wait("CANCEL_RIDE", {"ride_id": ride_id}, expected={"CANCEL_RIDE_OK", "CANCEL_RIDE_FAIL"})

    def list_contacts(self, user_id: int) -> Dict[str, Any]:
        return self._send_and_wait("LIST_CONTACTS", {"user_id": user_id}, expected={"CONTACTS"})

    def fetch_messages(self, user_id: int, partner_id: int) -> Dict[str, Any]:
        return self._send_and_wait("FETCH_MESSAGES", {"user_id": user_id, "partner_id": partner_id}, expected={"MESSAGES"})

    def send_message(self, to_username: str, message: str, attachment_filename: str = None, attachment_mime: str = None, attachment_data: str = None) -> Dict[str, Any]:
        payload = {"to": to_username, "message": message}
        if attachment_filename is not None:
            payload["attachment_filename"] = attachment_filename
        if attachment_mime is not None:
            payload["attachment_mime"] = attachment_mime
        if attachment_data is not None:
            payload["attachment_data"] = attachment_data
        return self._send_and_wait("SEND_MESSAGE", payload, expected={"SEND_MESSAGE_OK", "SEND_MESSAGE_FAIL"})

    def drain_events(self) -> List[ApiEvent]:
        events: List[ApiEvent] = []
        while True:
            try:
                msg = self._async_events.get_nowait()
            except Empty:
                break
            events.append(ApiEvent(type=msg.get("type", ""), payload=msg.get("payload", {})))
        return events

    # -----------------------------
    # Internal helpers
    # -----------------------------
    def _ensure_connection(self) -> socket.socket:
        if not self._sock or not self._connected:
            raise ApiClientError("Not connected to backend.")
        return self._sock

    def _send_and_wait(self, msg_type: str, payload: Dict[str, Any], expected: Iterable[str]) -> Dict[str, Any]:
        sock = self._ensure_connection()
        expected_types = set(expected)
        with self._send_lock:
            with self._wait_lock:
                if self._wait_types:
                    raise ApiClientError("Another request is already in-flight.")
                self._wait_types = expected_types
                self._wait_response = None
                self._wait_event.clear()
            send_json(sock, {"type": msg_type, "payload": payload})
        if not self._wait_event.wait(self.timeout):
            with self._wait_lock:
                self._wait_types = set()
            raise ApiClientError("Timed out waiting for server response.")
        with self._wait_lock:
            response = self._wait_response
            self._wait_response = None
        if response is None:
            raise ApiClientError("Did not receive response from server.")
        return response

    def _send_once(self, msg_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        message = {"type": msg_type, "payload": payload}
        try:
            with socket.create_connection((self.host, self.port), timeout=self.timeout) as conn:
                send_json(conn, message)
                response = recv_json(conn)
        except (ConnectionRefusedError, socket.timeout, OSError) as exc:
            raise ApiClientError(f"Unable to reach server: {exc}") from exc
        if response is None:
            raise ApiClientError("Server closed the connection without responding.")
        return response

    def _recv_loop(self) -> None:
        sock = self._ensure_connection()
        while self._connected:
            try:
                data = recv_json(sock)
            except (ConnectionResetError, OSError):
                data = None
            if not data:
                self._connected = False
                self._async_events.put({"type": "CONNECTION_LOST", "payload": {}})
                break
            handled = False
            with self._wait_lock:
                if self._wait_types and data.get("type") in self._wait_types:
                    self._wait_response = data
                    self._wait_types = set()
                    self._wait_event.set()
                    handled = True
            if not handled:
                self._async_events.put(data)
