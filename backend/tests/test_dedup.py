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


def test_dedup_within_window(client, registered_student, temp_db_path, monkeypatch):
    _backdate_register_attendance(temp_db_path, registered_student["id"])

    with open("tests/fixtures/face_known.jpg", "rb") as f:
        resp1 = client.post(
            "/api/recognize",
            files={"file": ("face_known.jpg", f, "image/jpeg")},
        )
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert "duplicate" not in data1
    assert data1["name"] == "Test Student"

    now = datetime.utcnow()
    monkeypatch.setattr("main._get_now", lambda: now)

    with open("tests/fixtures/face_known.jpg", "rb") as f:
        resp2 = client.post(
            "/api/recognize",
            files={"file": ("face_known.jpg", f, "image/jpeg")},
        )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2.get("duplicate") is True
    assert data2["name"] == "Test Student"

    conn = sqlite3.connect(temp_db_path)
    try:
        count = conn.execute(
            "SELECT COUNT(*) FROM attendance WHERE student_id = ? AND method = 'individual'",
            (registered_student["id"],),
        ).fetchone()[0]
        assert count == 2
    finally:
        conn.close()


def test_dedup_after_window(client, registered_student, temp_db_path):
    _backdate_register_attendance(temp_db_path, registered_student["id"])

    with open("tests/fixtures/face_known.jpg", "rb") as f:
        resp1 = client.post(
            "/api/recognize",
            files={"file": ("face_known.jpg", f, "image/jpeg")},
        )
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert "duplicate" not in data1

    old_ts = (datetime.utcnow() - timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(temp_db_path)
    try:
        conn.execute(
            "UPDATE attendance SET timestamp = ? WHERE student_id = ? AND type = 'check-in' "
            "AND method = 'individual'",
            (old_ts, registered_student["id"]),
        )
        conn.commit()
    finally:
        conn.close()

    with open("tests/fixtures/face_known.jpg", "rb") as f:
        resp2 = client.post(
            "/api/recognize",
            files={"file": ("face_known.jpg", f, "image/jpeg")},
        )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert "duplicate" not in data2
    assert data2["name"] == "Test Student"

    conn = sqlite3.connect(temp_db_path)
    try:
        count = conn.execute(
            "SELECT COUNT(*) FROM attendance WHERE student_id = ? AND method = 'individual'",
            (registered_student["id"],),
        ).fetchone()[0]
        assert count == 3
    finally:
        conn.close()


def test_dedup_group_within_window(
    client, registered_student, temp_db_path, monkeypatch
):
    _backdate_register_attendance(temp_db_path, registered_student["id"])

    with open("tests/fixtures/face_known.jpg", "rb") as f:
        resp1 = client.post(
            "/api/recognize-group",
            files={"file": ("face_known.jpg", f, "image/jpeg")},
        )
    assert resp1.status_code == 200
    matches1 = resp1.json()["matches"]
    assert len(matches1) >= 1
    assert "duplicate" not in matches1[0]

    now = datetime.utcnow()
    monkeypatch.setattr("main._get_now", lambda: now)

    with open("tests/fixtures/face_known.jpg", "rb") as f:
        resp2 = client.post(
            "/api/recognize-group",
            files={"file": ("face_known.jpg", f, "image/jpeg")},
        )
    assert resp2.status_code == 200
    matches2 = resp2.json()["matches"]
    assert len(matches2) >= 1
    assert matches2[0].get("duplicate") is True

    conn = sqlite3.connect(temp_db_path)
    try:
        count = conn.execute(
            "SELECT COUNT(*) FROM attendance WHERE student_id = ? AND method = 'group'",
            (registered_student["id"],),
        ).fetchone()[0]
        assert count == 1
    finally:
        conn.close()
