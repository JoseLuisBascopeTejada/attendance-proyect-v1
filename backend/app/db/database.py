import os
import sqlite3


def get_connection() -> sqlite3.Connection:
    db_path = os.getenv("DB_PATH", "/app/data/attendance.db")
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                embedding BLOB,
                photo_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                type TEXT CHECK(type IN ('check-in', 'check-out')),
                method TEXT CHECK(method IN ('individual', 'group')),
                FOREIGN KEY (student_id) REFERENCES students(id)
            )
            """
        )
        conn.commit()
    finally:
        conn.close()
