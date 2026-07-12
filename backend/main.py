import io
import logging
import math
import os
import tempfile
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

import numpy as np
from dotenv import load_dotenv
from fpdf import FPDF
from PIL import Image

load_dotenv()

from deepface import DeepFace
from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.core.ai_engine import (
    MIN_FACE_AREA_RATIO,
    cosine_distance,
    extract_embedding,
    get_detector_backend,
    get_model,
    warm_up,
)
from app.db.database import get_connection, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    warm_up()
    yield


app = FastAPI(title="Attendance API", version="0.1.0", lifespan=lifespan)

cors_origins = os.getenv("CORS_ORIGINS", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _get_now():
    return datetime.utcnow()


def validate_upload(contents: bytes):
    max_size = int(os.getenv("MAX_FILE_SIZE_MB", "5")) * 1024 * 1024
    max_width = int(os.getenv("MAX_IMAGE_WIDTH", "1920"))
    max_height = int(os.getenv("MAX_IMAGE_HEIGHT", "1080"))

    if len(contents) > max_size:
        raise HTTPException(status_code=413, detail="File too large. Max 5MB allowed.")

    try:
        img = Image.open(io.BytesIO(contents))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image file.")

    width, height = img.size
    if width > max_width or height > max_height:
        raise HTTPException(
            status_code=413,
            detail=f"Image dimensions too large. Max {max_width}x{max_height}px.",
        )
    return width, height


def check_duplicate(conn, student_id: int, now) -> bool:
    row = conn.execute(
        "SELECT timestamp FROM attendance WHERE student_id = ? AND type = 'check-in' "
        "ORDER BY timestamp DESC LIMIT 1",
        (student_id,),
    ).fetchone()
    if row is None:
        return False
    last_ts = datetime.fromisoformat(row[0])
    return (now - last_ts).total_seconds() < 300


@app.get("/")
def root():
    return {"service": "attendance-api", "version": "0.1.0"}


@app.get("/api/db-status")
def db_status():
    conn = get_connection()
    try:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row[0] for row in cursor.fetchall()]
        return {"status": "ok", "db": "connected", "tables": tables}
    finally:
        conn.close()


@app.post("/api/register")
async def register(file: UploadFile = File(...), name: str = Form(...)):
    face_confidence = float(os.getenv("FACE_CONFIDENCE", "0.90"))
    faces_dir = os.getenv("FACES_DIR", "/app/data/known_faces")

    contents = await file.read()
    width, height = validate_upload(contents)

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        detector = get_detector_backend()
        face_objs = DeepFace.extract_faces(
            img_path=tmp_path, detector_backend=detector, enforce_detection=False
        )

        # Check (a): no face at all
        if not face_objs:
            raise HTTPException(status_code=400, detail="No face detected.")

        # Check (b): more than one face
        if len(face_objs) > 1:
            raise HTTPException(
                status_code=400,
                detail="Multiple faces detected. Please use a photo with only one face.",
            )

        best_face = face_objs[0]

        # Check (c): confidence below threshold
        if best_face.get("confidence", 0) < face_confidence:
            raise HTTPException(
                status_code=400,
                detail="Face detected but image quality is too low. Please try again.",
            )

        # Check (d): face area too small relative to image
        if "width" not in locals() or "height" not in locals():
            raise HTTPException(status_code=400, detail="Could not determine image dimensions.")
        img_area = width * height
        area = best_face.get("facial_area", {})
        face_area = area.get("w", 0) * area.get("h", 0)
        if img_area > 0 and (face_area / img_area) < MIN_FACE_AREA_RATIO:
            raise HTTPException(
                status_code=400,
                detail="Face is too small in the frame. Please move closer to the camera.",
            )

        embedding = DeepFace.represent(
            img_path=tmp_path,
            model_name="Facenet",
            detector_backend=detector,
            enforce_detection=True,
        )[0]["embedding"]
        embedding_blob = np.array(embedding).tobytes()

        person_dir = Path(faces_dir) / name
        person_dir.mkdir(parents=True, exist_ok=True)
        ext = Path(file.filename or "img.jpg").suffix or ".jpg"
        filename = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{ext}"
        photo_path = person_dir / filename
        with open(photo_path, "wb") as f:
            f.write(contents)

        conn = get_connection()
        try:
            cursor = conn.execute(
                "INSERT INTO students (name, embedding, photo_path) VALUES (?, ?, ?)",
                (name, embedding_blob, str(photo_path)),
            )
            student_id = cursor.lastrowid
            conn.execute(
                "INSERT INTO attendance (student_id, type, method) VALUES (?, ?, ?)",
                (student_id, "check-in", "individual"),
            )
            conn.commit()
        finally:
            conn.close()

        return {"id": student_id, "name": name, "status": "registered"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unhandled error in register")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        os.unlink(tmp_path)


@app.post("/api/recognize")
async def recognize(file: UploadFile = File(...)):
    threshold = float(os.getenv("THRESHOLD", "0.4"))

    contents = await file.read()
    validate_upload(contents)

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        try:
            probe_embedding = extract_embedding(tmp_path)
        except Exception:
            raise HTTPException(status_code=404)

        conn = get_connection()
        try:
            rows = conn.execute("SELECT id, name, embedding FROM students").fetchall()
            if not rows:
                raise HTTPException(status_code=404)

            best_match = None
            best_distance = float("inf")
            for student_id, name, emb_blob in rows:
                db_embedding = np.frombuffer(emb_blob, dtype=np.float64).tolist()
                dist = cosine_distance(probe_embedding, db_embedding)
                if dist < best_distance:
                    best_distance = dist
                    best_match = (student_id, name)

            if best_match is None or best_distance >= threshold:
                raise HTTPException(status_code=404)

            student_id, name = best_match
            now = _get_now()
            duplicate = check_duplicate(conn, student_id, now)
            if not duplicate:
                conn.execute(
                    "INSERT INTO attendance (student_id, type, method) VALUES (?, ?, ?)",
                    (student_id, "check-in", "individual"),
                )
                conn.commit()

            result = {"name": name, "distance": best_distance, "student_id": student_id}
            if duplicate:
                result["duplicate"] = True
            return result
        finally:
            conn.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unhandled error in recognize")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        os.unlink(tmp_path)


@app.post("/api/recognize-group")
async def recognize_group(file: UploadFile = File(...)):
    threshold = float(os.getenv("THRESHOLD", "0.4"))

    contents = await file.read()
    validate_upload(contents)

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        detector = get_detector_backend()
        face_objs = DeepFace.extract_faces(
            img_path=tmp_path, detector_backend=detector, enforce_detection=False
        )
        if not face_objs:
            return {"matches": []}

        conn = get_connection()
        try:
            rows = conn.execute("SELECT id, name, embedding FROM students").fetchall()
            if not rows:
                return {"matches": []}

            db_students = [
                (sid, name, np.frombuffer(emb_blob, dtype=np.float64).tolist())
                for sid, name, emb_blob in rows
            ]

            matches = []
            for face in face_objs:
                area = face.get("facial_area", {})
                bbox = [area.get("x", 0), area.get("y", 0), area.get("w", 0), area.get("h", 0)]

                x, y, w, h = bbox
                pil_img = Image.open(tmp_path)
                face_crop = pil_img.crop((x, y, x + w, y + h))

                with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as face_tmp:
                    face_crop.save(face_tmp.name)
                    face_tmp_path = face_tmp.name

                try:
                    face_embedding = extract_embedding(face_tmp_path)
                finally:
                    os.unlink(face_tmp_path)

                best_match = None
                best_distance = float("inf")
                for sid, name, db_emb in db_students:
                    dist = cosine_distance(face_embedding, db_emb)
                    if dist < best_distance:
                        best_distance = dist
                        best_match = (sid, name)

                if best_match is not None and best_distance < threshold:
                    student_id, name = best_match
                    now = _get_now()
                    duplicate = check_duplicate(conn, student_id, now)
                    if not duplicate:
                        conn.execute(
                            "INSERT INTO attendance (student_id, type, method) VALUES (?, ?, ?)",
                            (student_id, "check-in", "group"),
                        )
                        conn.commit()

                    match_entry = {"name": name, "distance": best_distance, "bbox": bbox}
                    if duplicate:
                        match_entry["duplicate"] = True
                    matches.append(match_entry)

            return {"matches": matches}
        finally:
            conn.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unhandled error in recognize-group")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        os.unlink(tmp_path)


@app.get("/api/attendance")
def get_attendance(
    date_from: str = Query(None),
    date_to: str = Query(None),
    student_id: int = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
):
    conn = get_connection()
    try:
        where_clauses = []
        params = []

        if date_from:
            where_clauses.append("a.timestamp >= ?")
            params.append(date_from)
        if date_to:
            where_clauses.append("a.timestamp <= ?")
            params.append(date_to)
        if student_id is not None:
            where_clauses.append("a.student_id = ?")
            params.append(student_id)

        where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        total = conn.execute(
            f"SELECT COUNT(*) FROM attendance a{where_sql}", params
        ).fetchone()[0]

        pages = max(1, math.ceil(total / limit))
        offset = (page - 1) * limit

        rows = conn.execute(
            f"""
            SELECT a.id, a.student_id, s.name, a.timestamp, a.type, a.method
            FROM attendance a
            JOIN students s ON a.student_id = s.id
            {where_sql}
            ORDER BY a.timestamp DESC
            LIMIT ? OFFSET ?
            """,
            params + [limit, offset],
        ).fetchall()

        records = [
            {
                "id": row[0],
                "student_id": row[1],
                "name": row[2],
                "timestamp": row[3],
                "type": row[4],
                "method": row[5],
            }
            for row in rows
        ]

        return {"records": records, "total": total, "page": page, "pages": pages}
    finally:
        conn.close()


@app.get("/api/students")
def get_students():
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, name, photo_path, created_at FROM students ORDER BY id"
        ).fetchall()

        students = [
            {
                "id": row[0],
                "name": row[1],
                "photo_path": row[2],
                "created_at": row[3],
            }
            for row in rows
        ]

        return {"students": students}
    finally:
        conn.close()


@app.get("/api/report/pdf")
def get_report_pdf(
    date_from: str = Query(None),
    date_to: str = Query(None),
):
    conn = get_connection()
    try:
        where_clauses = []
        params = []

        if date_from:
            where_clauses.append("a.timestamp >= ?")
            params.append(date_from)
        if date_to:
            where_clauses.append("a.timestamp <= ?")
            params.append(date_to)

        where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        rows = conn.execute(
            f"""
            SELECT a.timestamp, s.name, a.type, a.method
            FROM attendance a
            JOIN students s ON a.student_id = s.id
            {where_sql}
            ORDER BY a.timestamp DESC
            """,
            params,
        ).fetchall()
    finally:
        conn.close()

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Attendance Report", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(5)

    if date_from or date_to:
        pdf.set_font("Helvetica", "", 10)
        filter_text = f"Filter: {date_from or '...'} to {date_to or '...'}"
        pdf.cell(0, 8, filter_text, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)

    pdf.set_font("Helvetica", "B", 11)
    col_widths = [45, 60, 35, 35]
    headers = ["Date", "Student", "Type", "Method"]
    for i, h in enumerate(headers):
        pdf.cell(col_widths[i], 8, h, border=1)
    pdf.ln()

    pdf.set_font("Helvetica", "", 10)
    if not rows:
        pdf.cell(0, 8, "No records found.", new_x="LMARGIN", new_y="NEXT")
    else:
        for row in rows:
            ts = row[0] if row[0] else ""
            name = row[1] if row[1] else ""
            typ = row[2] if row[2] else ""
            method = row[3] if row[3] else ""
            pdf.cell(col_widths[0], 8, str(ts)[:10], border=1)
            pdf.cell(col_widths[1], 8, str(name), border=1)
            pdf.cell(col_widths[2], 8, str(typ), border=1)
            pdf.cell(col_widths[3], 8, str(method), border=1)
            pdf.ln()

    pdf_bytes = pdf.output()
    return StreamingResponse(
        io.BytesIO(bytes(pdf_bytes)),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=attendance_report.pdf"},
    )
