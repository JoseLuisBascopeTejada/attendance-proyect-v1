import os

import numpy as np
from PIL import Image


def test_register_valid_face(client):
    with open("tests/fixtures/face_known.jpg", "rb") as f:
        resp = client.post(
            "/api/register",
            files={"file": ("face_known.jpg", f, "image/jpeg")},
            data={"name": "Alice"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data
    assert data["name"] == "Alice"
    assert data["status"] == "registered"


def test_register_no_face(client):
    with open("tests/fixtures/no_face.jpg", "rb") as f:
        resp = client.post(
            "/api/register",
            files={"file": ("no_face.jpg", f, "image/jpeg")},
            data={"name": "NoFace"},
        )
    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert detail in (
        "No face detected.",
        "Face detected but image quality is too low. Please try again.",
    )


def test_register_saves_embedding(client, temp_db_path):
    with open("tests/fixtures/face_known.jpg", "rb") as f:
        resp = client.post(
            "/api/register",
            files={"file": ("face_known.jpg", f, "image/jpeg")},
            data={"name": "EmbedCheck"},
        )
    assert resp.status_code == 200
    student_id = resp.json()["id"]

    import sqlite3

    conn = sqlite3.connect(temp_db_path)
    try:
        row = conn.execute(
            "SELECT embedding FROM students WHERE id=?", (student_id,)
        ).fetchone()
        assert row is not None
        assert row[0] is not None
        embedding = np.frombuffer(row[0], dtype=np.float64)
        assert len(embedding) > 0
    finally:
        conn.close()


def test_register_saves_photo(client, temp_faces_dir):
    with open("tests/fixtures/face_known.jpg", "rb") as f:
        resp = client.post(
            "/api/register",
            files={"file": ("face_known.jpg", f, "image/jpeg")},
            data={"name": "PhotoCheck"},
        )
    assert resp.status_code == 200

    person_dir = os.path.join(temp_faces_dir, "PhotoCheck")
    assert os.path.isdir(person_dir)
    files = os.listdir(person_dir)
    assert len(files) == 1
    assert os.path.getsize(os.path.join(person_dir, files[0])) > 0


def test_register_single_face(client):
    with open("tests/fixtures/face_known.jpg", "rb") as f:
        resp = client.post(
            "/api/register",
            files={"file": ("face_known.jpg", f, "image/jpeg")},
            data={"name": "SingleFace"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "registered"


def test_register_rejects_multiple_faces(client):
    base = Image.open("tests/fixtures/face_known.jpg")
    canvas = Image.new("RGB", (600, 300), (0, 0, 0))
    canvas.paste(base, (0, 0))
    canvas.paste(base, (300, 0))
    from io import BytesIO

    buf = BytesIO()
    canvas.save(buf, format="JPEG", quality=95)
    buf.seek(0)

    resp = client.post(
        "/api/register",
        files={"file": ("multi_face.jpg", buf, "image/jpeg")},
        data={"name": "MultiFace"},
    )
    assert resp.status_code == 400
    assert "Multiple faces detected" in resp.json()["detail"]


def test_register_rejects_small_face(client):
    base = Image.open("tests/fixtures/face_known.jpg")
    small = base.resize((100, 100), Image.LANCZOS)
    canvas = Image.new("RGB", (600, 600), (50, 50, 50))
    canvas.paste(small, (50, 50))
    from io import BytesIO

    buf = BytesIO()
    canvas.save(buf, format="JPEG", quality=85)
    buf.seek(0)

    resp = client.post(
        "/api/register",
        files={"file": ("small_face.jpg", buf, "image/jpeg")},
        data={"name": "SmallFace"},
    )
    assert resp.status_code == 400
    assert "too small" in resp.json()["detail"].lower()


def test_register_happy_path_realistic_image(client):
    img = Image.open("tests/fixtures/face_known.jpg")
    canvas = Image.new("RGB", (1280, 720), (100, 100, 100))
    big_face = img.resize((600, 600), Image.LANCZOS)
    canvas.paste(big_face, (340, 0))
    from io import BytesIO

    buf = BytesIO()
    canvas.save(buf, format="JPEG", quality=90)
    buf.seek(0)

    resp = client.post(
        "/api/register",
        files={"file": ("webcam.jpg", buf, "image/jpeg")},
        data={"name": "WebcamUser"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "WebcamUser"
    assert data["status"] == "registered"
