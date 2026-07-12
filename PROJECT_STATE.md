# Project State — Attendance Proyect v1

**Last updated:** 2026-07-12
**Status:** Backend FASE 0–5 (B0–B18) complete | Frontend FASE 2–4 (F1–F12) complete | FASE 6+ not yet started
**Tests:** 50/50 passing (pytest, Windows, no Docker)
**Docker:** `docker compose up --build` from repo root; backend + frontend both start

---

## 1. Tech Stack

**Backend dependencies** (verbatim from `backend/requirements.txt`):
```
fastapi
uvicorn[standard]
python-multipart
deepface
opencv-python<5
tf-keras
python-dotenv
pytest
httpx
Pillow
numpy
fpdf2
```
Plus `opencv-python==4.11.0.86` pinned via second pip install in Dockerfile.

**Frontend dependencies** (verbatim from `frontend/package.json`):
```json
"dependencies": {
    "axios": "^1.18.1",
    "react": "^19.2.7",
    "react-dom": "^19.2.7",
    "react-router-dom": "^7.18.1",
    "react-webcam": "^7.2.0"
}
```
No chart libraries. No icon libraries. No UI component libraries.

| Layer | Technology | Notes |
|---|---|---|
| Backend framework | FastAPI | Unpinned |
| ASGI server | Uvicorn `[standard]` | Unpinned |
| Face recognition | DeepFace + TensorFlow | `deepface` unpinned; `tf-keras` unpinned |
| Face detector | RetinaFace (default) | Configurable via `DETECTOR_BACKEND` env var |
| Face model | Facenet | Loaded once at startup via `get_model()`, cached globally in `ai_engine.py` |
| Database | SQLite 3 | File: `/app/data/attendance.db` (or `DB_PATH` env var) |
| ORM/Driver | `sqlite3` stdlib | Raw SQL via `get_connection()` in `database.py` |
| OpenCV | `opencv-python==4.11.0.86` | Pinned in Dockerfile; requires `libgl1` + `libglib2.0-0` |
| PDF generation | fpdf2 | Unpinned |
| Config | `python-dotenv` + `os.getenv()` | No pydantic-settings. `load_dotenv()` in `main.py:19` |
| Frontend framework | React 19 + TypeScript 6 | Vite 8 build tool; requires Node ≥20 |
| Package manager | pnpm | Lockfile: `pnpm-lock.yaml` |
| Frontend HTTP | axios | Base URL: `http://localhost:8000/api` (`src/api/client.ts`) |
| Camera | react-webcam | Used in Register, Recognize, RecognizeGroup pages |
| Routing | React Router v7 | `BrowserRouter` in `main.tsx`, routes in `App.tsx` |
| Testing | pytest + httpx (TestClient) | `conftest.py` provides client, model fixtures |

---

## 2. Directory Structure

```
attendance-proyect-v1/
├── backend/
│   ├── main.py                  # All 9 routes + helpers (validate_upload, check_duplicate, _normalize_date_to, _get_now)
│   ├── Dockerfile               # python:3.11-slim, --reload
│   ├── requirements.txt         # 12 deps (unpinned except opencv-python==4.11.0.86)
│   ├── .env.example             # 9 env vars
│   ├── app/
│   │   ├── __init__.py          # empty
│   │   ├── core/
│   │   │   ├── __init__.py      # empty
│   │   │   └── ai_engine.py     # get_detector_backend(), get_model(), warm_up(), extract_embedding(), cosine_distance()
│   │   └── db/
│   │       ├── __init__.py      # empty
│   │       └── database.py      # get_connection(), init_db()
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py          # 5 fixtures: temp_db_path, temp_faces_dir, client, model, registered_student
│       ├── fixtures/
│       │   ├── face_known.jpg
│       │   ├── no_face.jpg
│       │   └── large_image.jpg
│       ├── test_ai_engine.py
│       ├── test_attendance.py
│       ├── test_attendance_endpoint.py
│       ├── test_db.py
│       ├── test_dedup.py
│       ├── test_health.py
│       ├── test_image_validation.py
│       ├── test_recognize.py
│       ├── test_register.py
│       ├── test_report_pdf.py
│       ├── test_student_delete.py
│       └── test_students_endpoint.py
│
├── frontend/
│   ├── Dockerfile               # node:22-alpine build → nginx:alpine serve
│   ├── .dockerignore            # node_modules, dist, .git
│   ├── package.json
│   ├── pnpm-lock.yaml
│   ├── src/
│   │   ├── main.tsx             # BrowserRouter wrapping + ReactDOM.createRoot
│   │   ├── App.tsx              # Routes + Route definitions (4 routes)
│   │   ├── App.css              # App shell styles (sticky header, nav links)
│   │   ├── index.css            # Design tokens (CSS variables) + dark mode + reset
│   │   ├── api/
│   │   │   └── client.ts        # axios instance, baseURL http://localhost:8000/api
│   │   ├── components/
│   │   │   └── WebcamCapture.tsx # Reusable webcam + capture button
│   │   └── pages/
│   │       ├── Layout.tsx       # Sticky header nav + Outlet
│   │       ├── Dashboard.tsx    # Attendance table, date filters, summary cards, pagination, PDF download
│   │       ├── Register.tsx     # Name input + webcam capture form
│   │       ├── Recognize.tsx    # Webcam capture → single face recognition
│   │       └── RecognizeGroup.tsx # Webcam capture → multi-face recognition
│
├── data/
│   └── known_faces/             # Persistent face photos (Docker volume mount → /app/data)
│       └── Lucas Perez/         # 1 registered student
│
├── docker-compose.yml           # backend (8000) + frontend (3000→80)
├── PROJECT_STATE.md             # This file
└── agents/                      # Planning docs
```

**Notable absences:**
- No `app/routes/` directory — all routes live in `main.py`
- No `app/core/config.py` — config is `os.getenv()` throughout
- No `app/schemas.py` or `app/dependencies.py`
- No `nginx.conf` — frontend Docker uses default nginx config
- No `backend/.dockerignore`

---

## 3. Environment Variables

All 9 variables from `backend/.env.example`:

| Variable | Default | Description |
|---|---|---|
| `DB_PATH` | `/app/data/attendance.db` | SQLite database file path |
| `FACES_DIR` | `/app/data/known_faces` | Directory for registered face photos |
| `THRESHOLD` | `0.4` | Cosine distance threshold for recognition (lower = stricter) |
| `FACE_CONFIDENCE` | `0.90` | Minimum face detection confidence to accept a face |
| `MAX_FILE_SIZE_MB` | `5` | Maximum upload file size in megabytes |
| `MAX_IMAGE_WIDTH` | `1920` | Maximum image width for resize before processing |
| `MAX_IMAGE_HEIGHT` | `1080` | Maximum image height for resize before processing |
| `CORS_ORIGINS` | `*` | Allowed origins for CORS |
| `DETECTOR_BACKEND` | `retinaface` | Face detector: `retinaface`, `opencv`, `mtcnn`, `ssd`, `mediapipe` |

**Config access:** `os.getenv()` called directly in `main.py`, `database.py`, and `ai_engine.py`. No centralized config module.

**`DETECTOR_BACKEND` usage:** `get_detector_backend()` in `ai_engine.py:9` reads env var at call time. Used in `main.py` for register/recognize/recognize-group. `warm_up()` uses `detector_backend="skip"`.

---

## 4. Database Schema

From `backend/app/db/database.py:16-36`:

```sql
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    embedding BLOB,
    photo_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)

CREATE TABLE IF NOT EXISTS attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    type TEXT CHECK(type IN ('check-in', 'check-out')),
    method TEXT CHECK(method IN ('individual', 'group')),
    FOREIGN KEY (student_id) REFERENCES students(id)
)
```

**Notes:**
- `students.name` has **NO** `NOT NULL` constraint — the schema allows NULL names
- `attendance.type` is always `'check-in'` — `'check-out'` is in the CHECK constraint but never written by any endpoint
- Foreign key cascade: deleting a student deletes all their attendance records (via `PRAGMA foreign_keys = ON` in `get_connection()`)
- No migrations — tables created via `CREATE TABLE IF NOT EXISTS` on startup

---

## 5. API Endpoints

All routes defined in `backend/main.py`. Frontend axios base URL: `http://localhost:8000/api`.

| Method | Path | Request | Response | Line |
|---|---|---|---|---|
| `GET` | `/` | — | `{"service": "attendance-api", "version": "0.1.0"}` | `main.py:100` |
| `GET` | `/api/db-status` | — | `{"status": "ok", "db": "connected", "tables": [...]}` | `main.py:105` |
| `POST` | `/api/register` | FormData: `file` (image), `name` (string) | `{"id": N, "name": "...", "status": "registered"}` | `main.py:118` |
| `POST` | `/api/recognize` | FormData: `file` (image) | `{"name": "...", "distance": N, "student_id": N}` or `{"name": "...", "distance": N, "student_id": N, "duplicate": true}` | `main.py:209` |
| `POST` | `/api/recognize-group` | FormData: `file` (image) | `{"matches": [{"name": "...", "distance": N, "bbox": [x,y,w,h], "duplicate": true}, ...]}` | `main.py:269` |
| `GET` | `/api/attendance` | Query: `date_from`, `date_to`, `student_id`, `page` (default 1), `limit` (default 10) | `{"records": [...], "total": N, "page": N, "pages": N}` | `main.py:353` |
| `GET` | `/api/students` | — | `{"students": [{"id": N, "name": "...", "photo_path": "...", "created_at": "..."}, ...]}` | `main.py:414` |
| `DELETE` | `/api/students/{student_id}` | Path: `student_id` (int) | `{"status": "deleted", "student_id": N, "name": "..."}` | `main.py:437` |
| `GET` | `/api/report/pdf` | Query: `date_from`, `date_to` | PDF file (`application/pdf`, StreamingResponse) | `main.py:467` |

**Error responses** (all endpoints): `{"detail": "..."}` with status 400, 404, 413, or 500. Error handlers at `main.py:200-204` (register), `main.py:260-264` (recognize), `main.py:344-348` (recognize-group), `main.py:458-462` (delete-student) use `logger.exception()` + generic message.

**Helpers in main.py:**
- `_get_now()` (line 56): returns `datetime.utcnow()`
- `_normalize_date_to()` (line 60): appends ` 23:59:59` to plain 10-char dates
- `validate_upload()` (line 66): checks file size + image dimensions
- `check_duplicate()` (line 88): checks if student checked in within last 300 seconds
- `MIN_FACE_AREA_RATIO` (line 47): `float(os.getenv("MIN_FACE_AREA_RATIO", "0.05"))`

---

## 6. Test Suite

**Framework:** pytest + httpx (TestClient). **Location:** `backend/tests/`. **Run:** `pytest -v` from `backend/`.

**conftest.py fixtures (5):**
- `temp_db_path` (function-scoped): temp SQLite file path
- `temp_faces_dir` (function-scoped): temp faces directory
- `client` (function-scoped): sync TestClient with monkeypatched env vars (`DB_PATH`, `FACES_DIR`, `DETECTOR_BACKEND`)
- `model` (session-scoped): DeepFace model loaded once via `warm_up()` + `get_model()`
- `registered_student`: registers a test student via POST /api/register

**Test fixture files:** `face_known.jpg`, `no_face.jpg`, `large_image.jpg` (in `tests/fixtures/`)

**Per-file test counts** (verified via `def test_` grep, cross-checked against 50/50 pytest run):

| File | `def test_` count |
|---|---|
| `test_ai_engine.py` | 2 |
| `test_attendance.py` | 3 |
| `test_attendance_endpoint.py` | 7 |
| `test_db.py` | 5 |
| `test_dedup.py` | 3 |
| `test_health.py` | 2 |
| `test_image_validation.py` | 2 |
| `test_recognize.py` | 6 |
| `test_register.py` | 8 |
| `test_report_pdf.py` | 5 |
| `test_student_delete.py` | 4 |
| `test_students_endpoint.py` | 3 |
| **Total** | **50** |

**Sanity check:** 2+7+3+5+3+2+2+6+8+5+4+3 = 50 ✓ matches confirmed pytest count.

---

## 7. Frontend

**Stack:** React 19 + TypeScript 6 + Vite 8 + pnpm. **5 pages/components, no third-party UI libraries.**

### Imports verified from each file:

**`main.tsx`** (13 lines):
- `StrictMode` from `react`
- `createRoot` from `react-dom/client`
- `BrowserRouter` from `react-router-dom`
- `index.css`, `App.tsx`
- Wraps `<App />` in `<BrowserRouter>` and `<StrictMode>`

**`App.tsx`** (21 lines):
- `Routes`, `Route` from `react-router-dom`
- `Layout`, `Dashboard`, `Register`, `Recognize`, `RecognizeGroup`
- No `BrowserRouter` wrapping (that's in `main.tsx`)
- 4 routes under `<Layout />`: `/` → Dashboard, `/register` → Register, `/recognize` → Recognize, `/recognize-group` → RecognizeGroup

**`Layout.tsx`** (37 lines):
- `Outlet`, `Link`, `useLocation` from `react-router-dom`
- `../App.css`
- Uses `Link` (not `NavLink`) with manual active class via `useLocation().pathname`
- 4 nav items: Dashboard, Registrar, Reconocer, Reconocimiento Grupal
- Sticky header + `<Outlet />` for nested routes

**`Dashboard.tsx`** (352 lines):
- `useEffect`, `useState`, `useCallback`, `useRef` from `react`
- `apiClient` from `../api/client`
- No chart library. No icon library.
- Features: attendance records table, date range filter (from/to), summary cards (today's count + registered students), PDF download button, pagination (prev/next)
- Helper: `getTodayISO()` returns `YYYY-MM-DD` string

**`Register.tsx`** (198 lines):
- `useState`, `FormEvent` from `react`
- `apiClient`, `WebcamCapture`
- Name input + webcam capture form → POST `/api/register`
- `base64ToBlob()` helper
- Shows success/error feedback

**`Recognize.tsx`** (171 lines):
- `useState` from `react`
- `apiClient`, `WebcamCapture`
- Webcam capture → POST `/api/recognize`
- `base64ToBlob()` helper
- Shows matched name, distance, student_id, duplicate flag

**`RecognizeGroup.tsx`** (239 lines):
- `useRef`, `useState`, `useCallback` from `react`
- `Webcam` from `react-webcam` (direct, NOT using WebcamCapture component)
- `apiClient`
- Webcam capture → POST `/api/recognize-group`
- `resizeImage()` helper (client-side canvas resize to 800px max width)
- Shows list of matches with name, distance, bbox, duplicate flag

**`WebcamCapture.tsx`** (59 lines):
- `useCallback`, `useRef` from `react`
- `Webcam` from `react-webcam`
- Reusable component: webcam + "Capture Photo" button
- Props: `onCapture` callback, `width` (default 640), `height` (default 480)
- Used by `Register.tsx` and `Recognize.tsx`

**`client.ts`** (20 lines):
- `axios` instance with `baseURL: 'http://localhost:8000/api'`
- Response interceptor: shows `alert()` on error

**Styling:**
- `index.css` (56 lines): CSS custom properties (design tokens), dark mode via `prefers-color-scheme`, basic reset
- `App.css` (56 lines): App shell layout (flex column), sticky header, nav link styles with active state

---

## 8. Known Issues

| # | Severity | Description |
|---|---|---|
| 1 | Medium | **`CORS_ORIGINS=*`** — wildcard allows requests from any origin. Not recommended for production deployments. (`.env.example` line 8) |
| 2 | Medium | **Git working tree dirty** — `backend/main.py`, `backend/tests/test_attendance_endpoint.py`, `frontend/src/App.tsx` modified; `frontend/src/pages/Dashboard.tsx`, `frontend/src/pages/Layout.tsx` untracked. Needs commit. |
| 3 | Low | **Unpinned deps** — All backend deps except `opencv-python==4.11.0.86` are unpinned. Versions may drift on rebuild. |
| 4 | Low | **`students.name` has no NOT NULL constraint** — schema allows NULL names. (`database.py:19`) |
| 5 | Low | **No `nginx.conf`** — frontend Docker uses default nginx config. May need custom config for production (caching, gzip, security headers). |
| 6 | Info | **Attendance type is always `'check-in'`** — `'check-out'` is in the CHECK constraint but never written by any endpoint. |
| 7 | Info | **Frontend has no volume mount** — Code changes require `docker compose build frontend && docker compose up -d frontend`. Backend has volume mount (`./backend:/app`) with `--reload`. |
| 8 | Info | **Duplicate student names are allowed** — `students.name` has no UNIQUE constraint. Intentional design decision. |

---

## 9. Task Status

All tasks from `BACKEND_TASKS.md` and `FRONTEND_TASKS.md` are marked complete.

### Backend (B0–B18)
- B0–B5: Core setup (FastAPI, DB, AI engine, config, Docker)
- B6–B8: Register, Recognize, RecognizeGroup endpoints
- B9–B11: Attendance endpoint, PDF report, CORS
- B12–B14: Exception handlers, DETECTOR_BACKEND centralization, MIN_FACE_AREA_RATIO tuning
- B15–B18: Student delete endpoint + tests, date_to normalization

### Frontend (F1–F12)
- F1–F3: Project setup (Vite + React + TS), API client, routing
- F4–F6: Layout, Dashboard, Register page
- F7–F9: Recognize page, RecognizeGroup page, WebcamCapture component
- F10–F12: Styling (CSS variables, dark mode), polish

### FASE 6+ — Not yet started
- Face recognition accuracy tuning (THRESHOLD, detector selection)
- Production hardening (HTTPS, auth, rate limiting, logging)
- CI/CD pipeline
- E2E tests (Playwright/Cypress)
- Deployment (cloud/VPS)

---

## 10. Docker / Infrastructure

**`docker-compose.yml`:**
```yaml
services:
  backend:
    build: ./backend
    container_name: attendance_backend
    volumes:
      - ./backend:/app           # Hot reload with --reload
      - ./data:/app/data         # Persistent face photos + DB
    ports:
      - "8000:8000"
    environment:
      - PYTHONUNBUFFERED=1

  frontend:
    build: ./frontend
    container_name: attendance_frontend
    ports:
      - "3000:80"                # nginx serves on port 80 inside container
    depends_on:
      - backend
```

**Backend Dockerfile** (`backend/Dockerfile`):
- Base: `python:3.11-slim`
- Installs `libgl1`, `libglib2.0-0` (OpenCV system deps)
- `pip install -r requirements.txt` + `pip install "opencv-python==4.11.0.86"`
- Downloads `haarcascade_frontalface_default.xml` for OpenCV detector
- `CMD: ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]`

**Frontend Dockerfile** (`frontend/Dockerfile`):
- Multi-stage: `node:22-alpine` build → `nginx:alpine` serve
- `pnpm install` + `pnpm run build` → `dist/`
- Default nginx config (no custom `nginx.conf`)

---

## 11. Project Status Summary

**What works end-to-end:**
1. Register a face → photo saved, embedding computed and stored
2. Recognize a face → webcam capture, matched against DB, returns student name
3. Recognize group → multiple faces detected and matched simultaneously
4. Dashboard → attendance records displayed with date filtering and pagination
5. Attendance tracking → check-in records created on successful recognition
6. PDF report → generated for date range
7. Student management → list all, delete (with FK cascade + photo cleanup)

**What's not done:**
- FASE 6+: Accuracy tuning, production auth, HTTPS, CI/CD, E2E tests, deployment
- Dependency pinning for reproducible builds
- Git commit for current dirty working tree

**Quick start:**
```bash
# Start everything
docker compose up --build

# Backend: http://localhost:8000
# Frontend: http://localhost:3000

# Run tests (locally, no Docker)
cd backend && pytest -v
```
