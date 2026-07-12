import sqlite3
from datetime import datetime, timedelta


def _backdate_register_attendance(temp_db_path, student_id):
    old_ts = (datetime.utcnow() - timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(temp_db_path)
    try:
        conn.execute(
            "UPDATE attendance SET timestamp = ? WHERE student_id = ? AND type = 'check-in'",
            (old_ts, student_id),
        )
        conn.commit()
    finally:
        conn.close()


def test_attendance_recorded_on_recognize(client, registered_student, temp_db_path):
    _backdate_register_attendance(temp_db_path, registered_student["id"])

    with open("tests/fixtures/face_known.jpg", "rb") as f:
        resp = client.post(
            "/api/recognize",
            files={"file": ("face_known.jpg", f, "image/jpeg")},
        )
    assert resp.status_code == 200

    conn = sqlite3.connect(temp_db_path)
    try:
        rows = conn.execute(
            "SELECT student_id, type, method FROM attendance WHERE student_id = ? "
            "AND method = 'individual' ORDER BY timestamp DESC LIMIT 1",
            (registered_student["id"],),
        ).fetchall()
        assert len(rows) == 1
        assert rows[0][0] == registered_student["id"]
        assert rows[0][1] == "check-in"
        assert rows[0][2] == "individual"
    finally:
        conn.close()


def test_attendance_recorded_on_recognize_group(
    client, registered_student, temp_db_path
):
    _backdate_register_attendance(temp_db_path, registered_student["id"])

    with open("tests/fixtures/face_known.jpg", "rb") as f:
        resp = client.post(
            "/api/recognize-group",
            files={"file": ("face_known.jpg", f, "image/jpeg")},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["matches"]) >= 1

    conn = sqlite3.connect(temp_db_path)
    try:
        rows = conn.execute(
            "SELECT student_id, type, method FROM attendance WHERE student_id = ? "
            "AND method = 'group' ORDER BY timestamp DESC LIMIT 1",
            (registered_student["id"],),
        ).fetchall()
        assert len(rows) == 1
        assert rows[0][0] == registered_student["id"]
        assert rows[0][1] == "check-in"
        assert rows[0][2] == "group"
    finally:
        conn.close()


def test_attendance_links_student(client, registered_student, temp_db_path):
    _backdate_register_attendance(temp_db_path, registered_student["id"])

    with open("tests/fixtures/face_known.jpg", "rb") as f:
        client.post(
            "/api/recognize",
            files={"file": ("face_known.jpg", f, "image/jpeg")},
        )

    conn = sqlite3.connect(temp_db_path)
    try:
        row = conn.execute(
            "SELECT a.student_id, s.name FROM attendance a "
            "JOIN students s ON a.student_id = s.id "
            "WHERE a.student_id = ? LIMIT 1",
            (registered_student["id"],),
        ).fetchone()
        assert row is not None
        assert row[1] == "Test Student"
    finally:
        conn.close()
