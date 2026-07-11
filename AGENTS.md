# AGENTS.md

## Project

Facial-recognition attendance system. Two services via Docker Compose: Python/FastAPI backend + React/Vite/TypeScript frontend. Early-stage (scaffolded, few commits).

## Architecture

```
backend/   → FastAPI + DeepFace + OpenCV (Python 3.11)
frontend/  → React 19 + Vite 8 + TypeScript 6 + pnpm
data/      → shared volume mounted into backend container
```

- Backend entrypoint: `main:app` (uvicorn, port 8000) — `main.py` provides health, register, and recognize endpoints.
- Face database: `data/known_faces/{person_name}/` (volume-mounted, persistent).
- Frontend is still the Vite template scaffold; attendance UI not yet implemented.
- `react-webcam` and `axios` are installed as dependencies (camera + HTTP).

## Commands

### Docker (recommended)

```bash
docker compose up --build        # start both services
docker compose up --build -d     # detached
docker compose down
```

### Frontend (local dev)

```bash
cd frontend
pnpm install
pnpm run dev      # Vite dev server (port 5173)
pnpm run build    # tsc -b && vite build
pnpm run lint     # eslint .
```

### Backend (local dev, no Docker)

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

**No test runner is configured in either service yet.**

## Gotchas

- **Frontend Dockerfile requires Node 22+**: Vite 8 depends on `rolldown` which needs Node ≥20. The Dockerfile uses `node:22-alpine`. Do not downgrade to Node 18.
- **Frontend Docker builds need `CI=true` and `.dockerignore`**: Without these, `COPY . .` overwrites `node_modules` with the host's platform-specific copy, and pnpm fails trying to purge it in a non-TTY environment. The `.dockerignore` excludes `node_modules` and `dist`; `ENV CI=true` in the Dockerfile prevents the purge prompt.
- **Backend OpenCV system deps**: Dockerfile installs `libgl1` and `libglib2.0-0` for OpenCV. If adding a local (non-Docker) backend dev setup, these must be installed on the host too.
- **Backend python-multipart**: Required for FastAPI file uploads. Already in `requirements.txt`.
- **TypeScript strictness**: `noUnusedLocals`, `noUnusedParameters`, and `erasableSyntaxOnly` are enabled in `tsconfig.app.json`. Lint will fail on unused imports/variables.
- **Package manager**: Frontend uses **pnpm** (lockfile: `pnpm-lock.yaml`). Do not use npm or yarn.
- **`data/` directory**: Empty at root, volume-mounted into the backend container at `/app/data`. Used for runtime data (likely face models/datasets).

## Conventions

- No CI, no pre-commit hooks, no code formatter beyond ESLint.
- No test framework installed yet.
- Backend dependencies are unpinned in `requirements.txt` (no version specifiers).
- The `agents/` directory holds planning docs (`PLAN.md` currently empty).
