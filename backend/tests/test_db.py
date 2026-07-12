import sqlite3

from app.db.database import get_connection, init_db


def test_db_connection(client, temp_db_path):
    import os

    os.environ["DB_PATH"] = temp_db_path
    conn = get_connection()
    assert isinstance(conn, sqlite3.Connection)
    conn.close()


def test_init_db_creates_tables(client):
    conn = get_connection()
    try:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row[0] for row in cursor.fetchall()]
        assert "students" in tables
        assert "attendance" in tables
    finally:
        conn.close()


def test_insert_student(client):
    conn = get_connection()
    try:
        conn.execute("INSERT INTO students (name) VALUES (?)", ("Alice",))
        conn.commit()
        row = conn.execute("SELECT name FROM students WHERE name='Alice'").fetchone()
        assert row is not None
        assert row[0] == "Alice"
    finally:
        conn.close()


def test_insert_duplicate_name(client):
    conn = get_connection()
    try:
        conn.execute("INSERT INTO students (name) VALUES (?)", ("Bob",))
        conn.commit()
        conn.execute("INSERT INTO students (name) VALUES (?)", ("Bob",))
        conn.commit()
        rows = conn.execute("SELECT name FROM students WHERE name='Bob'").fetchall()
        assert len(rows) == 2
    finally:
        conn.close()


def test_attendance_insert(client):
    conn = get_connection()
    try:
        conn.execute("INSERT INTO students (name) VALUES (?)", ("Charlie",))
        conn.commit()
        student = conn.execute(
            "SELECT id FROM students WHERE name='Charlie'"
        ).fetchone()
        student_id = student[0]
        conn.execute(
            "INSERT INTO attendance (student_id, type, method) VALUES (?, ?, ?)",
            (student_id, "check-in", "individual"),
        )
        conn.commit()
        row = conn.execute(
            "SELECT student_id, type, method FROM attendance WHERE student_id=?",
            (student_id,),
        ).fetchone()
        assert row is not None
        assert row[1] == "check-in"
        assert row[2] == "individual"
    finally:
        conn.close()
