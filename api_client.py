import json
import socket
from dataclasses import dataclass
from typing import Any, Dict, Optional


class ApiClientError(Exception):
    """Raised when the frontend cannot communicate with the backend server."""


@dataclass
class ApiResponse:
    type: str
    payload: Optional[Dict[str, Any]]


class ApiClient:
    """Thin TCP client that speaks the JSON protocol defined in /server."""

    def __init__(self, host: str = "127.0.0.1", port: int = 5555, timeout: float = 5.0) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout

    def register(self, name: str, email: str, username: str, password: str) -> ApiResponse:
        return self._send("REGISTER", {"name": name, "email": email, "username": username, "password": password})

    def login(self, username: str, password: str) -> ApiResponse:
        return self._send("LOGIN", {"username": username, "password": password})

    def _send(self, msg_type: str, payload: Dict[str, Any]) -> ApiResponse:
        message = {"type": msg_type, "payload": payload}
        try:
            with socket.create_connection((self.host, self.port), timeout=self.timeout) as conn:
                self._send_json(conn, message)
                response = self._recv_json(conn)
        except (ConnectionRefusedError, socket.timeout, OSError) as exc:
            raise ApiClientError(f"Unable to reach server: {exc}") from exc

        if response is None:
            raise ApiClientError("Server closed the connection without responding.")

        return ApiResponse(type=response.get("type", ""), payload=response.get("payload"))

    @staticmethod
    def _send_json(conn: socket.socket, data: Dict[str, Any]) -> None:
        msg = json.dumps(data) + "\n"
        conn.sendall(msg.encode())

    @staticmethod
    def _recv_json(conn: socket.socket) -> Optional[Dict[str, Any]]:
        data = conn.recv(4096)
        if not data:
            return None
        return json.loads(data.decode().strip())
