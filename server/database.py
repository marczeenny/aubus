import sqlite3

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
            area TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            day TEXT NOT NULL,
            time TEXT NOT NULL,
            direction TEXT NOT NULL,
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

    conn.commit()
    conn.close()


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
    c.execute("SELECT id, name, email, is_driver, area FROM users WHERE username=? AND password=?",
              (username, password))
    user = c.fetchone()
    conn.close()
    if user:
        return {"user_id": user[0], "name": user[1], "email": user[2], "is_driver": bool(user[3]), "area": user[4], "username": username}
    return None


def set_driver_profile(user_id, is_driver, area):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE users SET is_driver=?, area=? WHERE id=?", (int(is_driver), area, user_id))
    conn.commit()
    conn.close()


# -----------------------------
# Schedule
# -----------------------------
def add_schedule(user_id, day, time, direction):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO schedules (user_id, day, time, direction) VALUES (?, ?, ?, ?)",
              (user_id, day, time, direction))
    conn.commit()
    conn.close()


# -----------------------------
# Rides
# -----------------------------
def save_ride(passenger_id, driver_id, day, time, area, status="PENDING"):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO rides (passenger_id, driver_id, day, time, area, status) VALUES (?, ?, ?, ?, ?, ?)",
              (passenger_id, driver_id, day, time, area, status))
    conn.commit()
    ride_id = c.lastrowid
    conn.close()
    return ride_id


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
def add_rating(rated_user_id, rater_user_id, rating, role, ride_id=None):
    conn = get_conn()
    c = conn.cursor()
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
