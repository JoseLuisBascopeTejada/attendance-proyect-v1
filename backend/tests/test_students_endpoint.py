def test_get_students_empty(client):
    resp = client.get("/api/students")
    assert resp.status_code == 200
    data = resp.json()
    assert data["students"] == []


def test_get_students_list(client, registered_student):
    resp = client.get("/api/students")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["students"]) >= 1
    student = data["students"][0]
    assert student["id"] == registered_student["id"]
    assert student["name"] == "Test Student"
    assert "photo_path" in student
    assert "created_at" in student


def test_get_students_fields(client, registered_student):
    resp = client.get("/api/students")
    data = resp.json()
    student = data["students"][0]
    expected_keys = {"id", "name", "photo_path", "created_at"}
    assert set(student.keys()) == expected_keys
