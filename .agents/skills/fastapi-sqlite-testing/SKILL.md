---
name: fastapi-sqlite-testing
description: Use this skill whenever writing or editing any file under backend/tests/ in the facial-recognition attendance project — conftest.py, fixtures, or any test_*.py file. Also consult it when a task says "create tests for FASE X" or asks to run pytest. It defines the required fixture patterns (in-memory DB, isolated FACES_DIR, session-scoped model, image fixtures) needed so tests never touch real production data, never leak state between test files, and never accidentally reload the DeepFace model per test.
---

# Backend Testing Patterns — pytest + httpx + FastAPI

## The two rules that matter most

1. **Tests must never touch the real database or the real `FACES_DIR`.**
   Every test run uses an isolated, throwaway SQLite DB and a temp folder
   for face images. If a test fixture points at the real `DB_PATH` from
   `.env`, a bug in a test could corrupt real attendance data.
2. **Tests must never reload the DeepFace model per test.** See the
   `deepface-model-lifecycle` skill — the same "load once" rule applies
   inside the test suite via a session-scoped fixture.

## Required conftest.py shape

```python
import pytest
import os
import tempfile
from fastapi.testclient import TestClient

@pytest.fixture(scope="function")
def temp_db_path(tmp_path):
    """A fresh SQLite file per test function — isolated, not :memory:
    if the app opens multiple connections (in-memory DBs are NOT shared
    across connections unless using a shared cache URI)."""
    return str(tmp_path / "test_attendance.db")

@pytest.fixture(scope="function")
def temp_faces_dir(tmp_path):
    d = tmp_path / "known_faces"
    d.mkdir()
    return str(d)

@pytest.fixture(scope="function")
def client(temp_db_path, temp_faces_dir, monkeypatch):
    """TestClient wired to isolated DB/faces dir via env vars, NOT the
    real .env values."""
    monkeypatch.setenv("DB_PATH", temp_db_path)
    monkeypatch.setenv("FACES_DIR", temp_faces_dir)
    from main import app
    from app.db.database import init_db
    init_db()
    with TestClient(app) as c:
        yield c

@pytest.fixture(scope="session")
def model():
    """Loaded once for the whole test session — see
    deepface-model-lifecycle skill."""
    from app.core.ai_engine import get_model, warm_up
    warm_up()
    return get_model()
```

**Critical detail on SQLite `:memory:`:** if `get_connection()` opens a new
connection per call (which is typical for a simple `sqlite3.connect(...)`
pattern), `:memory:` databases do NOT persist across connections — each
connection gets its own empty in-memory DB, and your tests will silently
fail to find data they just inserted. Either:
- use a real temp file path (`tmp_path / "test.db"`, as above), or
- use the shared-cache URI form: `file::memory:?cache=shared` with
  `sqlite3.connect(..., uri=True)` and keep the connection open for the
  test's duration.

Prefer the temp-file approach — it's what `BACKEND_TASKS.md` fixtures
assume, and it more closely matches real production behavior.

## Fixture images — what each one must actually contain

| Fixture file | Must contain | Used to test |
|---|---|---|
| `fixtures/face_known.jpg` | A single clear, front-facing human face | Happy-path register/recognize |
| `fixtures/no_face.jpg` | A landscape/object photo with zero faces | 400 error on register |
| `fixtures/large_image.jpg` | A real JPEG over `MAX_FILE_SIZE_MB` (5MB) or exceeding `MAX_IMAGE_WIDTH`x`MAX_IMAGE_HEIGHT` | 413 error on register/recognize |

Don't fake these with 1x1 pixel stubs or empty files — DeepFace's face
detector needs an actual decodable image to produce a meaningful
pass/fail, and a corrupt fixture will make tests pass for the wrong reason
(a crash caught by a broad `except`, not a real validation check).

## Registering a fixture student for recognize/attendance tests

Recognition, dedup, and attendance tests need a student already in the DB
with a real embedding — don't hand-write a fake embedding BLOB, since a
made-up vector won't produce a realistic cosine distance against a probe
image and can make threshold tests pass or fail for the wrong reason.

```python
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
```

## Testing the dedup window (5 minutes) without actually waiting

Don't `time.sleep(300)` in a test. Instead, either:
- monkeypatch/inject the "now" timestamp used by the attendance-insert
  logic so tests can simulate elapsed time, or
- insert a row directly via the DB connection with a backdated
  `timestamp` value, then call `/api/recognize` and assert a new row
  *is* inserted (testing "after the window") vs. asserting no new row
  when the backdated timestamp is inside the 5-minute window.

If the endpoint code doesn't currently support timestamp injection for
testing, that's a sign the endpoint should accept `datetime.now()` via
a small internal helper you can monkeypatch, rather than calling
`datetime.now()` inline in five different places.

## One test file, one concern

Match test files to the phase/feature they test — don't let
`test_recognize.py` also contain attendance-dedup assertions; that
belongs in `test_dedup.py` per `BACKEND_TASKS.md`. Keeping this separation
makes it possible to run `pytest tests/test_dedup.py -v` in isolation when
iterating on dedup logic specifically.

## Before marking a testing task done

- [ ] Run the specific phase's test files, not just `pytest` blindly, to
      confirm you're testing what the task actually asked for.
- [ ] Confirm no test fixture references the real `.env` `DB_PATH` or
      `FACES_DIR`.
- [ ] Confirm the DeepFace model fixture is `session`-scoped, not
      `function`-scoped.
- [ ] Run the full suite (`pytest tests/ -v`) at least once before
      declaring a phase complete, to catch cross-file state leakage.