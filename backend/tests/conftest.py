import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="function")
def temp_db_path(tmp_path):
    return str(tmp_path / "test_attendance.db")


@pytest.fixture(scope="function")
def temp_faces_dir(tmp_path):
    d = tmp_path / "known_faces"
    d.mkdir()
    return str(d)


@pytest.fixture(scope="function")
def client(temp_db_path, temp_faces_dir, monkeypatch):
    monkeypatch.setenv("DB_PATH", temp_db_path)
    monkeypatch.setenv("FACES_DIR", temp_faces_dir)
    monkeypatch.setenv("DETECTOR_BACKEND", "retinaface")
    from main import app
    from app.db.database import init_db

    init_db()
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def model():
    from app.core.ai_engine import get_model, warm_up

    warm_up()
    return get_model()


@pytest.fixture
def registered_student(client):
    with open("tests/fixtures/face_known.jpg", "rb") as f:
        resp = client.post(
            "/api/register",
            files={"file": ("face_known.jpg", f, "image/jpeg")},
            data={"name": "Test Student"},
        )
    assert resp.status_code == 200
    return resp.json()
