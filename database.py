import sqlite3

def create_db():
    conn = sqlite3.connect("emotions.db")
    cursor = conn.cursor()

    # Emotions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS emotions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER DEFAULT 1,
        message TEXT,
        emotion TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL,
        family_code TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Families table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS families (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        family_code TEXT UNIQUE NOT NULL,
        child_id INTEGER,
        parent_id INTEGER,
        therapist_id INTEGER
    )
    """)

    conn.commit()
    conn.close()

def insert_data(message, emotion, user_id=1):
    conn = sqlite3.connect("emotions.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO emotions (message, emotion, user_id) VALUES (?, ?, ?)",
        (message, emotion, user_id)
    )
    conn.commit()
    conn.close()

def get_user_by_email(email):
    conn = sqlite3.connect("emotions.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()
    return user

def get_user_by_id(user_id):
    conn = sqlite3.connect("emotions.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def create_user(name, email, password_hash, role, family_code):
    conn = sqlite3.connect("emotions.db")
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (name, email, password, role, family_code) VALUES (?, ?, ?, ?, ?)",
            (name, email, password_hash, role, family_code)
        )
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        return user_id
    except sqlite3.IntegrityError:
        conn.close()
        return None

def link_family(family_code, user_id, role):
    conn = sqlite3.connect("emotions.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM families WHERE family_code = ?", (family_code,))
    family = cursor.fetchone()
    if family:
        if role == "parent":
            cursor.execute(
                "UPDATE families SET parent_id = ? WHERE family_code = ?",
                (user_id, family_code)
            )
        elif role == "therapist":
            cursor.execute(
                "UPDATE families SET therapist_id = ? WHERE family_code = ?",
                (user_id, family_code)
            )
    else:
        if role == "child":
            cursor.execute(
                "INSERT INTO families (family_code, child_id) VALUES (?, ?)",
                (family_code, user_id)
            )
    conn.commit()
    conn.close()

def get_child_id_by_family(family_code):
    conn = sqlite3.connect("emotions.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT child_id FROM families WHERE family_code = ?",
        (family_code,)
    )
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None