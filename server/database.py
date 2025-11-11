import sqlite3

DB_FILE = "aubus.db"


# -----------------------------
# Utility: open connection
# -----------------------------
def get_conn():
    return sqlite3.connect(DB_FILE, check_same_thread=False)


# -----------------------------
# Initialize database & tables
# -----------------------------
def init_db():
    conn = get_conn()
    c = conn.cursor()

    # Users table
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            is_driver INTEGER DEFAULT 0,
            area TEXT,
            rating REAL DEFAULT 0,
            rating_count INTEGER DEFAULT 0
        )
    """)

    # Schedules table
    c.execute("""
        CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            day TEXT NOT NULL,
            time TEXT NOT NULL,
            direction TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Rides table
    c.execute("""
        CREATE TABLE IF NOT EXISTS rides (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            passenger_id INTEGER,
            driver_id INTEGER,
            day TEXT,
            time TEXT,
            area TEXT,
            status TEXT,
            FOREIGN KEY (passenger_id) REFERENCES users(id),
            FOREIGN KEY (driver_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()


# -----------------------------
# User registration & login
# -----------------------------
def add_user(name, email, username, password):
    try:
        conn = get_conn()
        c = conn.cursor()
        c.execute("""
            INSERT INTO users (name, email, username, password)
            VALUES (?, ?, ?, ?)
        """, (name, email, username, password))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        # Username already exists
        return False


def authenticate_user(username, password):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT id, name, email, is_driver, area, rating
        FROM users
        WHERE username=? AND password=?
    """, (username, password))
    user = c.fetchone()
    conn.close()

    if user:
        return {
            "user_id": user[0],
            "name": user[1],
            "email": user[2],
            "is_driver": bool(user[3]),
            "area": user[4],
            "rating": user[5],
            "username": username
        }
    else:
        return None


# -----------------------------
# Driver profile management
# -----------------------------
def set_driver_profile(user_id, is_driver, area):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        UPDATE users
        SET is_driver=?, area=?
        WHERE id=?
    """, (int(is_driver), area, user_id))
    conn.commit()
    conn.close()


# -----------------------------
# Scheduling management
# -----------------------------
def add_schedule(user_id, day, time, direction):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO schedules (user_id, day, time, direction)
        VALUES (?, ?, ?, ?)
    """, (user_id, day, time, direction))
    conn.commit()
    conn.close()


# -----------------------------
# Ride management
# -----------------------------
def get_drivers_in_area_time(area, day, time, min_rating=0):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT u.id, u.name, u.username, u.rating, u.area, s.time
        FROM users u
        JOIN schedules s ON u.id = s.user_id
        WHERE u.is_driver=1
          AND u.area=?
          AND s.day=?
          AND s.time=?
          AND u.rating >= ?
    """, (area, day, time, min_rating))
    drivers = c.fetchall()
    conn.close()

    return [
        {
            "id": d[0],
            "name": d[1],
            "username": d[2],
            "rating": d[3],
            "area": d[4],
            "time": d[5]
        }
        for d in drivers
    ]


def save_ride(passenger_id, driver_id, day, time, area, status="PENDING"):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO rides (passenger_id, driver_id, day, time, area, status)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (passenger_id, driver_id, day, time, area, status))
    conn.commit()
    conn.close()


# -----------------------------
# Ratings
# -----------------------------
def add_rating(user_id, rating):
    conn = get_conn()
    c = conn.cursor()
    # get old rating
    c.execute("SELECT rating, rating_count FROM users WHERE id=?", (user_id,))
    old = c.fetchone()
    if not old:
        conn.close()
        return
    old_rating, count = old
    new_count = count + 1
    new_rating = ((old_rating * count) + rating) / new_count
    c.execute("UPDATE users SET rating=?, rating_count=? WHERE id=?",
              (new_rating, new_count, user_id))
    conn.commit()
    conn.close()
