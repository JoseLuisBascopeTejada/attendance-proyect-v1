import os
import sqlite3

from PIL import Image


def test_delete_student_success(client):
    with open("tests/fixtures/face_known.jpg", "rb") as f:
        resp = client.post(
            "/api/register",
            files={"file": ("face_known.jpg", f, "image/jpeg")},
            data={"name": "ToDelete"},
        )
    assert resp.status_code == 200
    student_id = resp.json()["id"]

    resp = client.delete(f"/api/students/{student_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "deleted"
    assert data["student_id"] == student_id
    assert data["name"] == "ToDelete"


def test_delete_student_not_found(client):
    resp = client.delete("/api/students/99999")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Student not found"


def test_delete_student_removes_folder(client, temp_faces_dir):
    with open("tests/fixtures/face_known.jpg", "rb") as f:
        resp = client.post(
            "/api/register",
            files={"file": ("face_known.jpg", f, "image/jpeg")},
            data={"name": "FolderCheck"},
        )
    assert resp.status_code == 200
    student_id = resp.json()["id"]

    person_dir = os.path.join(temp_faces_dir, "FolderCheck")
    assert os.path.isdir(person_dir)

    resp = client.delete(f"/api/students/{student_id}")
    assert resp.status_code == 200

    assert not os.path.exists(person_dir)


def test_delete_student_removes_attendance_records(client, temp_db_path):
    with open("tests/fixtures/face_known.jpg", "rb") as f:
        resp = client.post(
            "/api/register",
            files={"file": ("face_known.jpg", f, "image/jpeg")},
            data={"name": "AttendDelete"},
        )
    assert resp.status_code == 200
    student_id = resp.json()["id"]

    conn = sqlite3.connect(temp_db_path)
    try:
        rows = conn.execute(
            "SELECT id FROM attendance WHERE student_id = ?", (student_id,)
        ).fetchall()
        assert len(rows) >= 1
    finally:
        conn.close()

    resp = client.delete(f"/api/students/{student_id}")
    assert resp.status_code == 200

    conn = sqlite3.connect(temp_db_path)
    try:
        rows = conn.execute(
            "SELECT id FROM attendance WHERE student_id = ?", (student_id,)
        ).fetchall()
        assert len(rows) == 0
        student_row = conn.execute(
            "SELECT id FROM students WHERE id = ?", (student_id,)
        ).fetchone()
        assert student_row is None
    finally:
        conn.close()
