import os
import tempfile
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from deepface import DeepFace

app = FastAPI(title="Attendance API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "/app/data/known_faces"
Path(DB_PATH).mkdir(parents=True, exist_ok=True)


@app.get("/")
def root():
    return {"service": "attendance-api", "version": "0.1.0"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/register")
def register(
    file: UploadFile = File(...),
    name: str = Form(...),
):
    person_dir = Path(DB_PATH) / name
    person_dir.mkdir(parents=True, exist_ok=True)

    ext = Path(file.filename or "img.jpg").suffix or ".jpg"
    filename = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{ext}"
    dest = person_dir / filename

    with open(dest, "wb") as f:
        f.write(file.file.read())

    return {"status": "registered", "name": name, "file": str(dest)}


@app.post("/recognize")
def recognize(file: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp.write(file.file.read())
        tmp_path = tmp.name

    try:
        results = DeepFace.find(
            img_path=tmp_path,
            db_path=DB_PATH,
            enforce_detection=True,
        )

        if not results or results[0].empty:
            raise HTTPException(status_code=404, detail="No face match found")

        best = results[0].iloc[0]
        identity = str(best["identity"])
        person_name = Path(identity).parent.name
        distance = float(best["distance"])

        return {
            "name": person_name,
            "distance": distance,
            "matched_file": identity,
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        os.unlink(tmp_path)
