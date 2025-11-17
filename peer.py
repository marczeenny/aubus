import socket
import threading
import json
from typing import Callable, Optional

class PeerServer:
    """Listens for incoming peer connections and dispatches JSON messages to a callback.

    callback signature: fn(peer_addr, message_dict)
    """
    def __init__(self, host='0.0.0.0', port=0, on_message: Optional[Callable]=None):
        self.host = host
        self.port = port
        self.on_message = on_message
        self._sock = None
        self._running = False
        self._thread = None

    def start(self):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((self.host, self.port))
        self._sock.listen(5)
        self.port = self._sock.getsockname()[1]
        self._running = True
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()
        try:
            print(f"[PeerServer] started listening on {self.host}:{self.port}")
        except Exception:
            pass
        return self.port

    def _serve(self):
        while self._running:
            try:
                conn, addr = self._sock.accept()
            except OSError:
                break
            try:
                print(f"[PeerServer] incoming connection from {addr}")
            except Exception:
                pass
            threading.Thread(target=self._handle_conn, args=(conn, addr), daemon=True).start()

    def _handle_conn(self, conn, addr):
        try:
            data = b''
            while True:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                data += chunk
            if not data:
                return
            try:
                msg = json.loads(data.decode().strip())
            except Exception:
                return
            try:
                print(f"[PeerServer] received from {addr}: {msg}")
            except Exception:
                pass
            if self.on_message:
                try:
                    self.on_message(addr, msg)
                except Exception:
                    pass
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def stop(self):
        self._running = False
        try:
            self._sock.close()
        except Exception:
            pass


def peer_send(ip: str, port: int, message: dict, timeout: float = 3.0):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        print(f"[peer_send] connecting to {ip}:{port} message={message}")
        s.connect((ip, port))
        s.sendall((json.dumps(message) + "\n").encode())
        # optionally read response (not required)
        try:
            resp = s.recv(4096)
            if resp:
                try:
                    return json.loads(resp.decode().strip())
                except Exception:
                    return None
        except Exception:
            return None
    finally:
        try:
            s.close()
        except Exception:
            pass
    return None
