"""Simple newline-terminated JSON send/receive helpers for server/client.

`send_json` appends a newline to each message. `recv_json` reads until the
first newline to support longer JSON payloads (e.g., base64 attachments).
"""

import json

# -----------------------------
# Send JSON over TCP
# -----------------------------
def send_json(conn, data):
    """
    Send a Python dictionary as a JSON string over the socket.
    Appends a newline for readability (optional).
    """
    msg = json.dumps(data) + "\n"
    conn.sendall(msg.encode())


# -----------------------------
# Receive JSON over TCP
# -----------------------------
def recv_json(conn):
    """
    Receive a JSON message from the socket.
    Assumes the message fits within 4096 bytes.
    """
    try:
        # Read until newline is found to support larger messages (e.g. base64 attachments).
        buf = b""
        max_bytes = 10 * 1024 * 1024  # 10 MB safety limit
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                # connection closed
                if not buf:
                    return None
                break
            buf += chunk
            if b"\n" in buf:
                # take data up to the first newline
                idx = buf.find(b"\n")
                msg_bytes = buf[:idx]
                try:
                    msg = msg_bytes.decode().strip()
                    return json.loads(msg)
                except json.JSONDecodeError as e:
                    print("JSON decode error:", e)
                    return None
            if len(buf) > max_bytes:
                print("recv_json: message too large")
                return None
        # If we exited the loop without a newline, attempt to decode whatever we have
        try:
            msg = buf.decode().strip()
            return json.loads(msg)
        except json.JSONDecodeError as e:
            print("JSON decode error:", e)
            return None
    except ConnectionResetError:
        return None
