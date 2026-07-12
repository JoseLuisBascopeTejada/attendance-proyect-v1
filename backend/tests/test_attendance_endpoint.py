import sqlite3
from datetime import datetime, timedelta


def _register_student(client, name="Test Student"):
    with open("tests/fixtures/face_known.jpg", "rb") as f:
        resp = client.post(
            "/api/register",
            files={"file": ("face_known.jpg", f, "image/jpeg")},
            data={"name": name},
        )
    assert resp.status_code == 200
    return resp.json()


def _backdate_all_attendance(temp_db_path, minutes_ago=10):
    old_ts = (datetime.utcnow() - timedelta(minutes=minutes_ago)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    conn = sqlite3.connect(temp_db_path)
    try:
        conn.execute("UPDATE attendance SET timestamp = ?", (old_ts,))
        conn.commit()
    finally:
        conn.close()


def test_get_attendance_empty(client):
    resp = client.get("/api/attendance")
    assert resp.status_code == 200
    data = resp.json()
    assert data["records"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["pages"] == 1


def test_get_attendance_with_data(client, registered_student, temp_db_path):
    _backdate_all_attendance(temp_db_path)

    resp = client.get("/api/attendance")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    record = data["records"][0]
    assert "id" in record
    assert "student_id" in record
    assert record["name"] == "Test Student"
    assert "timestamp" in record
    assert record["type"] == "check-in"
    assert record["method"] == "individual"


def test_get_attendance_pagination(client, registered_student, temp_db_path):
    _backdate_all_attendance(temp_db_path)

    _register_student(client, "Second Student")

    resp = client.get("/api/attendance?page=1&limit=1")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["records"]) == 1
    assert data["total"] >= 2
    assert data["page"] == 1
    assert data["pages"] >= 2


def test_get_attendance_filter_student(client, registered_student, temp_db_path):
    _backdate_all_attendance(temp_db_path)

    student_id = registered_student["id"]
    resp = client.get(f"/api/attendance?student_id={student_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    for record in data["records"]:
        assert record["student_id"] == student_id


def test_get_attendance_filter_date(client, registered_student, temp_db_path):
    _backdate_all_attendance(temp_db_path, minutes_ago=10)

    today = datetime.utcnow().strftime("%Y-%m-%d")
    tomorrow = (datetime.utcnow() + timedelta(days=1)).strftime("%Y-%m-%d")

    resp = client.get(f"/api/attendance?date_from={today}&date_to={tomorrow}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1


def test_get_attendance_last_partial_page(client, registered_student, temp_db_path):
    _backdate_all_attendance(temp_db_path)

    resp = client.get("/api/attendance?page=100&limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert data["records"] == []
    assert data["page"] == 100
