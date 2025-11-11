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
        data = conn.recv(4096)
        if not data:
            return None
        # Strip newline if present
        msg = data.decode().strip()
        return json.loads(msg)
    except json.JSONDecodeError as e:
        print("JSON decode error:", e)
        return None
    except ConnectionResetError:
        return None
