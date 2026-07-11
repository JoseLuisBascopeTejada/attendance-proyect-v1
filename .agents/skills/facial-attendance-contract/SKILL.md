---
name: facial-attendance-contract
description: Use this skill for ANY backend work on the facial-recognition attendance system (FastAPI + SQLite + DeepFace project) — writing endpoints, touching the database schema, adding environment variables, or writing tests. It contains the fixed, non-negotiable contract (DB schema, route prefix, env var names, response shapes, validation limits) that every task must match exactly. Always consult this skill BEFORE creating or editing main.py, app/db/database.py, app/core/ai_engine.py, .env files, or any tests/test_*.py file in this project, even if the task seems simple — this project has a documented history of schema drift and route-prefix mismatches between backend and frontend, and this skill exists specifically to prevent repeating those errors.
---

# Facial Attendance System — Backend Contract

This skill is the single source of truth for the parts of this codebase that
must stay byte-for-byte consistent across every task and every session:
the database schema, the API route prefix, environment variable names, and
response shapes. Treat everything in this file as fixed unless the user
explicitly tells you to change it — and if they do, tell them which other
files/skills also need to be updated to match (see "Propagation" at the end).

## 1. Critical rule: route prefix

**Every single route in this backend is registered under `/api/`.**

```python
# CORRECT
@app.get("/api/db-status")
@app.post("/api/register")
@app.post("/api/recognize")

# WRONG — this is the #1 bug in this project's history
@app.get("/db-status")
@app.post("/register")
```

The frontend's axios `baseURL` already includes `/api`. If you register a
route without the prefix, the frontend will get 404s on every request and
it will look like a frontend bug when it's actually a backend mismatch.
Before finishing any task that adds a route, grep your own diff for `@app.`
and confirm every path starts with `/api/`.

## 2. Database schema (exact — do not "improve" it)

```sql
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,                    -- NO UNIQUE constraint, NO NOT NULL
    embedding BLOB,
    photo_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    type TEXT CHECK(type IN ('check-in','check-out')),
    method TEXT CHECK(method IN ('individual','group')),
    FOREIGN KEY (student_id) REFERENCES students(id)
);
```

**Common mistakes to actively avoid here:**
- Adding `UNIQUE` to `students.name`. Duplicate names are an intentional,
  tested requirement (the same student may be registered more than once,
  or two students may share a name). If you add UNIQUE, `POST /api/register`
  will start throwing IntegrityErrors on legitimate input and
  `test_insert_duplicate_name` will fail.
- Adding a `recognized_by` column to `attendance`. That column belonged to
  an earlier, abandoned version of this schema. Use `type` and `method`
  instead — they are what every downstream endpoint (`/api/attendance`,
  `/api/report/pdf`, dedup logic) expects.
- Forgetting `IF NOT EXISTS` — `init_db()` must be safe to call on every
  app startup, not just once.

## 3. File locations (exact paths)

```
backend/
  main.py
  requirements.txt
  .env                      # gitignored, dev values
  .env.example              # committed, no real secrets
  app/
    db/
      database.py           # get_connection(), init_db() — plain functions, NOT a class
    core/
      ai_engine.py           # get_model(), extract_embedding(), warm_up()
  tests/
    conftest.py
    fixtures/
    test_*.py
```

Do not create `backend/db.py` or `backend/models.py` at the project root —
those paths belonged to an earlier abandoned plan and will conflict with
imports elsewhere in the codebase that expect the `app/` package structure.

## 4. Environment variables (exact names)

Read these from `.env` via `python-dotenv` / `os.getenv()`. Never hardcode
the values they represent anywhere else in the code — if you find yourself
writing a literal like `0.4` or `5 * 1024 * 1024` in a request handler,
stop and pull it from the env var instead.

| Variable | Meaning | Used by |
|---|---|---|
| `DB_PATH` | SQLite file path | `app/db/database.py` |
| `FACES_DIR` | Where registered face photos are stored | register/delete endpoints |
| `THRESHOLD` | Cosine distance cutoff for a recognition match (default 0.4) | `/api/recognize`, `/api/recognize-group` |
| `FACE_CONFIDENCE` | Minimum face-detection confidence (default 0.90) | `/api/register` |
| `MAX_FILE_SIZE_MB` | Upload size limit (default 5) | register/recognize endpoints |
| `MAX_IMAGE_WIDTH` / `MAX_IMAGE_HEIGHT` | Upload dimension limit (default 1920x1080) | register/recognize endpoints |
| `CORS_ORIGINS` | Allowed CORS origins | `main.py` app setup |

## 5. Validation error shapes (exact — the frontend pattern-matches on these)

```python
# File too large (>MAX_FILE_SIZE_MB)
raise HTTPException(status_code=413, detail="File too large. Max 5MB allowed.")

# Dimensions too large (>MAX_IMAGE_WIDTH x MAX_IMAGE_HEIGHT)
raise HTTPException(status_code=413, detail="Image dimensions too large. Max 1920x1080px.")

# No face detected in /api/register
raise HTTPException(status_code=400, detail="No face detected.")  # keep 400, not 422

# No match in /api/recognize
raise HTTPException(status_code=404)
```

Apply the size/dimension checks in **every** endpoint that accepts an
upload (`/api/register`, `/api/recognize`, `/api/recognize-group`) — it's
easy to add this validation to the first endpoint you write and forget to
repeat it on the other two.

## 6. Response shapes (exact keys, exact casing)

| Endpoint | Success response |
|---|---|
| `GET /api/db-status` | `{"status": "ok", "db": "connected", "tables": ["students", "attendance"]}` |
| `POST /api/register` | `{"id": <int>, "name": <str>, "status": "registered"}` |
| `POST /api/recognize` | `{"name": <str>, "distance": <float>, "student_id": <int>}` (add `"duplicate": true` if within the 5-min dedup window) |
| `POST /api/recognize-group` | `{"matches": [{"name": <str>, "distance": <float>, "bbox": [...]}]}` |
| `GET /api/attendance` | `{"records": [...], "total": <int>, "page": <int>, "pages": <int>}` |
| `GET /api/students` | `{"students": [{"id","name","photo_path","created_at"}]}` |
| `DELETE /api/students/{id}` | `{"status": "deleted", "student_id": <int>, "name": <str>}` |
| `GET /api/report/pdf` | binary, `Content-Type: application/pdf` |

Do not rename keys (e.g. `student_name` instead of `name`) even if it reads
better — the frontend destructures these exact keys.

## 7. Business rules that are easy to forget

- **Dedup window:** before inserting into `attendance`, check the most
  recent `check-in` for that `student_id`. If it's less than 5 minutes old,
  do not insert a new row — respond as normal but include
  `"duplicate": true`.
- **Match threshold:** a recognition is only a match if cosine distance is
  **below** `THRESHOLD` (default 0.4) — lower distance = more similar.
  Double-check the comparison direction (`distance < threshold`, not `>`).
- **Delete cascade:** `DELETE /api/students/{id}` must remove the DB row
  AND the `FACES_DIR/{name}/` folder on disk. A 404 must be returned if the
  student doesn't exist — check existence before attempting deletion.

## 8. Propagation

If you ever need to change anything in this file (a route, the schema, a
response shape), that change must also be reflected in:
- `PLAN.md` (sections 3, 4, 5 — the authoritative contract doc)
- `BACKEND_TASKS.md` (the task description that produced it)
- Flag it explicitly to the user, since the frontend agent works off the
  same contract and won't know about the change otherwise.