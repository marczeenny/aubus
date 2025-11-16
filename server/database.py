import sqlite3
from datetime import datetime, timedelta

DB_FILE = "aubus.db"


def get_conn():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            is_driver INTEGER DEFAULT 0,
            area TEXT,
            role_selected INTEGER DEFAULT 0
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            day TEXT NOT NULL,
            time TEXT NOT NULL,
            direction TEXT NOT NULL,
            area TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS rides (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            passenger_id INTEGER,
            driver_id INTEGER,
            day TEXT,
            time TEXT,
            area TEXT,
            status TEXT,
            requested_at TEXT DEFAULT CURRENT_TIMESTAMP,
            started_at TEXT,
            completed_at TEXT,
            FOREIGN KEY(passenger_id) REFERENCES users(id),
            FOREIGN KEY(driver_id) REFERENCES users(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rated_user_id INTEGER NOT NULL,
            rater_user_id INTEGER NOT NULL,
            rating INTEGER NOT NULL,
            role TEXT NOT NULL,
            ride_id INTEGER,
            FOREIGN KEY(rated_user_id) REFERENCES users(id),
            FOREIGN KEY(rater_user_id) REFERENCES users(id),
            FOREIGN KEY(ride_id) REFERENCES rides(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            body TEXT NOT NULL,
            sent_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(sender_id) REFERENCES users(id),
            FOREIGN KEY(receiver_id) REFERENCES users(id)
        )
    """)

    _ensure_column(c, "users", "role_selected", "INTEGER DEFAULT 0")
    _ensure_column(c, "rides", "requested_at", "TEXT DEFAULT CURRENT_TIMESTAMP")
    _ensure_column(c, "rides", "started_at", "TEXT")
    _ensure_column(c, "rides", "completed_at", "TEXT")
    _ensure_column(c, "schedules", "area", "TEXT")

    conn.commit()
    conn.close()


def _ensure_column(cursor, table, column, definition):
    try:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
    except sqlite3.OperationalError as exc:
        if "duplicate column name" not in str(exc):
            raise


# -----------------------------
# Users
# -----------------------------
def add_user(name, email, username, password):
    try:
        conn = get_conn()
        c = conn.cursor()
        c.execute("INSERT INTO users (name, email, username, password) VALUES (?, ?, ?, ?)",
                  (name, email, username, password))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False


def authenticate_user(username, password):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id, name, email, is_driver, area, role_selected FROM users WHERE username=? AND password=?",
              (username, password))
    user = c.fetchone()
    conn.close()
    if user:
        return {
            "user_id": user[0],
            "name": user[1],
            "email": user[2],
            "is_driver": bool(user[3]),
            "area": user[4],
            "role_selected": bool(user[5]),
            "username": username
        }
    return None


def get_user_by_username(username):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id, name, email, username, is_driver, area FROM users WHERE username=?", (username,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    return {"id": row[0], "name": row[1], "email": row[2], "username": row[3], "is_driver": bool(row[4]), "area": row[5]}


def get_user_by_id(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id, name, email, username, is_driver, area FROM users WHERE id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    return {"id": row[0], "name": row[1], "email": row[2], "username": row[3], "is_driver": bool(row[4]), "area": row[5]}


def set_user_role(user_id, role, area):
    conn = get_conn()
    c = conn.cursor()
    is_driver = 1 if role == "driver" else 0
    c.execute("UPDATE users SET is_driver=?, area=?, role_selected=1 WHERE id=?", (is_driver, area, user_id))
    conn.commit()
    conn.close()


# -----------------------------
# Schedule
# -----------------------------
def add_schedule(user_id, day, time, direction, area):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO schedules (user_id, day, time, direction, area) VALUES (?, ?, ?, ?, ?)",
              (user_id, day, time, direction, area))
    conn.commit()
    conn.close()


def get_schedule_entries(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id, day, time, direction, area FROM schedules WHERE user_id=? ORDER BY day, time", (user_id,))
    rows = c.fetchall()
    conn.close()
    return [{"id": row[0], "day": row[1], "time": row[2], "direction": row[3], "area": row[4]} for row in rows]


def delete_schedule_entry(schedule_id, user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM schedules WHERE id=? AND user_id=?", (schedule_id, user_id))
    conn.commit()
    conn.close()


def delete_schedule_for_user(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM schedules WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()


# -----------------------------
# Rides
# -----------------------------
def save_ride(passenger_id, driver_id, day, time, area, status="PENDING"):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO rides (passenger_id, driver_id, day, time, area, status, requested_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (passenger_id, driver_id, day, time, area, status, datetime.utcnow().isoformat()))
    conn.commit()
    ride_id = c.lastrowid
    conn.close()
    return ride_id


def start_ride(ride_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE rides SET status=?, started_at=? WHERE id=?", ("STARTED", datetime.utcnow().isoformat(), ride_id))
    conn.commit()
    conn.close()


def complete_ride(ride_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE rides SET status=?, completed_at=? WHERE id=?", ("COMPLETED", datetime.utcnow().isoformat(), ride_id))
    conn.commit()
    conn.close()


def update_ride_status(ride_id, status):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE rides SET status=? WHERE id=?", (status, ride_id))
    conn.commit()
    conn.close()


def get_user_rides(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT r.id, r.passenger_id, p.name, r.driver_id, d.name, r.day, r.time,
               r.area, r.status, r.completed_at, r.started_at, r.requested_at,
               (SELECT rating FROM ratings WHERE ride_id=r.id AND rater_user_id=?)
        FROM rides r
        LEFT JOIN users p ON r.passenger_id = p.id
        LEFT JOIN users d ON r.driver_id = d.id
        WHERE r.passenger_id=? OR r.driver_id=?
        ORDER BY COALESCE(r.completed_at, r.started_at, r.requested_at) DESC
    """, (user_id, user_id, user_id))
    rows = c.fetchall()
    conn.close()
    rides = []
    for row in rows:
        ride_id, passenger_id, passenger_name, driver_id, driver_name, day, time, area, status, completed_at, started_at, requested_at, rating = row
        role = "passenger" if user_id == passenger_id else "driver"
        partner_name = driver_name if role == "passenger" else passenger_name
        can_rate = False
        if completed_at:
            completed_dt = datetime.fromisoformat(completed_at)
            can_rate = datetime.utcnow() - completed_dt <= timedelta(hours=36)
        rides.append({
            "ride_id": ride_id,
            "role": role,
            "partner_name": partner_name,
            "day": day,
            "time": time,
            "area": area,
            "status": status,
            "completed_at": completed_at,
            "started_at": started_at,
            "requested_at": requested_at,
            "rating": rating,
            "can_edit_rating": can_rate
        })
    return rides


def get_pending_rides_for_driver(driver_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT r.id, r.passenger_id, u.name, u.username, r.day, r.time, r.area, r.status
        FROM rides r
        JOIN users u ON r.passenger_id = u.id
        WHERE r.driver_id=? AND r.status='REQUESTED'
        ORDER BY r.requested_at DESC
    """, (driver_id,))
    pending = [{"ride_id": row[0], "passenger_id": row[1], "passenger_name": row[2],
                "passenger_username": row[3], "day": row[4], "time": row[5],
                "area": row[6], "status": row[7]} for row in c.fetchall()]
    conn.close()
    return pending


def get_ride_by_id(ride_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT id, passenger_id, driver_id, day, time, area, status, requested_at, started_at, completed_at
        FROM rides WHERE id=?
    """, (ride_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "id": row[0],
        "passenger_id": row[1],
        "driver_id": row[2],
        "day": row[3],
        "time": row[4],
        "area": row[5],
        "status": row[6],
        "requested_at": row[7],
        "started_at": row[8],
        "completed_at": row[9]
    }


def get_drivers_in_area_time(area, day, time, min_rating=0):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT u.id, u.name, u.username,
               COALESCE(AVG(r.rating),0) as avg_rating,
               u.area, s.time
        FROM users u
        LEFT JOIN ratings r ON u.id = r.rated_user_id AND r.role='driver'
        JOIN schedules s ON u.id = s.user_id
        WHERE u.is_driver=1 AND u.area=? AND s.day=? AND s.time>=?
        GROUP BY u.id
        HAVING avg_rating >= ?
    """, (area, day, time, min_rating))
    drivers = c.fetchall()
    conn.close()
    return [{"id": d[0], "name": d[1], "username": d[2], "rating": d[3], "area": d[4], "time": d[5]} for d in drivers]


# -----------------------------
# Ratings
# -----------------------------
def upsert_rating(rated_user_id, rater_user_id, rating, role, ride_id):
    conn = get_conn()
    c = conn.cursor()
    existing = c.execute("SELECT id FROM ratings WHERE ride_id=? AND rater_user_id=?", (ride_id, rater_user_id)).fetchone()
    if existing:
        c.execute("UPDATE ratings SET rated_user_id=?, rating=?, role=? WHERE id=?",
                  (rated_user_id, rating, role, existing[0]))
    else:
        c.execute("""
            INSERT INTO ratings (rated_user_id, rater_user_id, rating, role, ride_id)
            VALUES (?, ?, ?, ?, ?)
        """, (rated_user_id, rater_user_id, rating, role, ride_id))
    conn.commit()
    conn.close()


def get_average_rating(user_id, role):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT AVG(rating) FROM ratings WHERE rated_user_id=? AND role=?", (user_id, role))
    avg = c.fetchone()[0]
    conn.close()
    return avg or 0


# -----------------------------
# Messages
# -----------------------------
def save_message(sender_id, receiver_id, body):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO messages (sender_id, receiver_id, body, sent_at)
        VALUES (?, ?, ?, ?)
    """, (sender_id, receiver_id, body, datetime.utcnow().isoformat()))
    conn.commit()
    msg_id = c.lastrowid
    sent_at = c.execute("SELECT sent_at FROM messages WHERE id=?", (msg_id,)).fetchone()[0]
    conn.close()
    return {"id": msg_id, "sent_at": sent_at}


def fetch_messages(user_id, partner_id, limit=50):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT sender_id, receiver_id, body, sent_at
        FROM messages
        WHERE (sender_id=? AND receiver_id=?) OR (sender_id=? AND receiver_id=?)
        ORDER BY sent_at DESC
        LIMIT ?
    """, (user_id, partner_id, partner_id, user_id, limit))
    rows = c.fetchall()
    conn.close()
    return [{"sender_id": r[0], "receiver_id": r[1], "body": r[2], "sent_at": r[3]} for r in reversed(rows)]


def list_contacts(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT DISTINCT CASE WHEN passenger_id=? THEN driver_id ELSE passenger_id END AS partner_id
        FROM rides
        WHERE (passenger_id=? OR driver_id=?)
              AND driver_id IS NOT NULL AND passenger_id IS NOT NULL
    """, (user_id, user_id, user_id))
    ride_partners = {row[0] for row in c.fetchall() if row[0]}

    c.execute("""
        SELECT DISTINCT CASE WHEN sender_id=? THEN receiver_id ELSE sender_id END AS partner_id
        FROM messages
        WHERE sender_id=? OR receiver_id=?
    """, (user_id, user_id, user_id))
    ride_partners.update(row[0] for row in c.fetchall() if row[0])
    partners = []
    for partner_id in ride_partners:
        user = get_user_by_id(partner_id)
        if user:
            partners.append(user)
    return partners
