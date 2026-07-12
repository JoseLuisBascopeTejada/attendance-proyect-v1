from io import BytesIO

from PIL import Image


def test_recognize_match_found(client, registered_student):
    with open("tests/fixtures/face_known.jpg", "rb") as f:
        resp = client.post(
            "/api/recognize",
            files={"file": ("face_known.jpg", f, "image/jpeg")},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Test Student"
    assert data["student_id"] == registered_student["id"]
    assert isinstance(data["distance"], float)
    assert data["distance"] < 0.4


def test_recognize_no_match(client, registered_student):
    with open("tests/fixtures/no_face.jpg", "rb") as f:
        resp = client.post(
            "/api/recognize",
            files={"file": ("no_face.jpg", f, "image/jpeg")},
        )
    assert resp.status_code == 404


def test_recognize_file_too_large(client, registered_student):
    with open("tests/fixtures/large_image.jpg", "rb") as f:
        resp = client.post(
            "/api/recognize",
            files={"file": ("large_image.jpg", f, "image/jpeg")},
        )
    assert resp.status_code == 413
    assert resp.json()["detail"] == "File too large. Max 5MB allowed."


def test_recognize_dimensions_too_large(client, registered_student):
    img = Image.new("RGB", (3000, 2000), (100, 150, 200))
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=95)
    buf.seek(0)

    resp = client.post(
        "/api/recognize",
        files={"file": ("big_dim.jpg", buf, "image/jpeg")},
    )
    assert resp.status_code == 413
    assert "Image dimensions too large" in resp.json()["detail"]


def test_recognize_empty_db(client):
    with open("tests/fixtures/face_known.jpg", "rb") as f:
        resp = client.post(
            "/api/recognize",
            files={"file": ("face_known.jpg", f, "image/jpeg")},
        )
    assert resp.status_code == 404


def test_recognize_matches_registered_student(client):
    with open("tests/fixtures/face_known.jpg", "rb") as f:
        resp = client.post(
            "/api/register",
            files={"file": ("face_known.jpg", f, "image/jpeg")},
            data={"name": "RoundTrip"},
        )
    assert resp.status_code == 200
    student_id = resp.json()["id"]

    with open("tests/fixtures/face_known.jpg", "rb") as f:
        resp = client.post(
            "/api/recognize",
            files={"file": ("face_known.jpg", f, "image/jpeg")},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "RoundTrip"
    assert data["student_id"] == student_id
    assert data["distance"] < 0.4
