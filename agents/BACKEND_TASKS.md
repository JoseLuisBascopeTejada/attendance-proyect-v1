# BACKEND_TASKS.md — Tareas del Backend

> Todas las tareas del backend organizadas por fase. Cada tarea incluye archivos a crear/modificar, que hacer, y criterios de aceptacion.

---

## FASE 0: Configuracion

### B0. Crear backend/.env.example — Variables de entorno
- **Archivos:**
  - backend/.env.example (crear)
  - backend/.env (crear con valores de desarrollo)
  - backend/main.py (modificar para cargar dotenv)
- **Descripcion:**
  - Definir todas las variables de entorno del proyecto:
    - DB_PATH=/app/data/attendance.db
    - FACES_DIR=/app/data/known_faces
    - THRESHOLD=0.4
    - FACE_CONFIDENCE=0.90
    - MAX_FILE_SIZE_MB=5
    - MAX_IMAGE_WIDTH=1920
    - MAX_IMAGE_HEIGHT=1080
    - CORS_ORIGINS=*
  - Cargar con python-dotenv o os.getenv() en main.py
  - .env.example (sin valores reales) se commitea; .env va en .gitignore
- **Criterio:** El backend lee variables del entorno; cambiar THRESHOLD=0.5 en .env cambia el comportamiento del reconocimiento

---

## FASE 1: Base de Datos y Conexion

> **NOTA CRITICA — VOLUMEN DOCKER:**
> Asegurar que /app/data este montada como volumen en docker-compose.yml para persistir la base de datos y las imagenes entre reinicios:
> ```yaml
> volumes:
>   - ./data:/app/data
> ```

### B1. Crear backend/app/db/database.py — SQLite
- **Archivos:** backend/app/db/database.py (crear)
- **Descripcion:**
  - Funciones get_connection() e init_db() (sin clase singleton)
  - Conexion SQLite a la ruta definida en variable de entorno DB_PATH
  - Crear tablas students y attendance al iniciar
- **Esquema:**
  ```sql
  students (id INTEGER PRIMARY KEY, name TEXT, embedding BLOB, photo_path TEXT, created_at TIMESTAMP)
  attendance (id INTEGER PRIMARY KEY, student_id INTEGER FK, timestamp TIMESTAMP, type TEXT CHECK(type IN ('check-in','check-out')), method TEXT CHECK(method IN ('individual','group')))
  ```
  > **NOTA:** El campo name NO tiene constraint UNIQUE — permite nombres repetidos (mismo estudiante registrado mas de una vez, o nombres similares).
- **Criterio:** init_db() crea tablas, get_connection() retorna conexion, name puede repetirse

### B2. Crear backend/app/core/ai_engine.py — Motor de IA
- **Archivos:** backend/app/core/ai_engine.py (crear)
- **Descripcion:**
  - Variable de modulo `model` cargada en el startup de FastAPI (DeepFace.build_model("Facenet"))
  - Mantener modelo en memoria (no recargar)
  - **Warm-up al iniciar el contenedor:** Ejecutar una inferencia dummy (imagen de prueba de 160x160 px) en el evento startup de FastAPI. Esto descarga y compila los modelos una vez, evitando latencia de ~10-15s en la primera peticion real.
  - Funciones: get_model(), extract_embedding(img_path), warm_up()
- **Criterio:** La primera peticion de reconocimiento no tiene latencia de carga

### B3. Agregar GET /api/db-status endpoint
- **Archivos:** backend/main.py (modificar)
- **Descripcion:**
  - Nuevo endpoint GET /api/db-status
  - Verificar conexion SQLite
  - Retornar {"status": "ok", "db": "connected", "tables": ["students", "attendance"]}
- **Depende:** B1
- **Criterio:** curl localhost:8000/api/db-status retorna JSON con estado

### B4. Crear tests de FASE 1
- **Archivos:**
  - backend/tests/__init__.py (crear)
  - backend/tests/conftest.py (crear)
  - backend/tests/test_db.py (crear)
  - backend/tests/test_ai_engine.py (crear)
  - backend/tests/test_health.py (crear)
  - backend/tests/fixtures/ (crear directorio)
- **Descripcion:**
  - conftest.py: fixtures para DB temporal (:memory:), TestClient FastAPI
  - test_db.py: test_db_connection, test_insert_student, test_insert_duplicate_name, test_attendance_insert
  - test_ai_engine.py: test_model_load, test_warm_up
  - test_health.py: test_health_endpoint, test_db_status_endpoint
- **Depende:** B1, B2, B3
- **Criterio:** pytest tests/test_db.py tests/test_ai_engine.py tests/test_health.py -v todos pasan

---

## FASE 2: Registro de Estudiantes

### B5. Mejorar POST /api/register — validacion + embedding
- **Archivos:** backend/main.py (modificar)
- **Descripcion:**
  - Recibir imagen + nombre
  - **Validar tamano de archivo: maximo 5MB.** Si excede, retornar error 413 {"detail": "File too large. Max 5MB allowed."}
  - **Validar dimensiones de imagen:** maximo 1920x1080 px para evitar colapsos de memoria. Si excede, retornar error 413 {"detail": "Image dimensions too large. Max 1920x1080px."}
  - Validar cara detectada (OpenCV/MTCNN) con confianza > 0.90
  - Extraer embedding con DeepFace (DeepFace.represent())
  - Guardar embedding como BLOB en tabla students
  - Guardar imagen en data/known_faces/{nombre}/
  - Insertar en attendance: type='check-in', method='individual'
  - Retornar {"id": ..., "name": ..., "status": "registered"}
  - Error 400 si no hay cara
- **Depende:** B1, B2
- **Criterio:** curl -X POST -F "file=@foto.jpg" -F "name=Juan" localhost:8000/api/register retorna ID; archivo >5MB retorna 413

### B6. Crear tests de FASE 2
- **Archivos:**
  - backend/tests/test_register.py (crear)
  - backend/tests/test_image_validation.py (crear)
  - backend/tests/fixtures/face_known.jpg (crear/colocar imagen de prueba)
  - backend/tests/fixtures/no_face.jpg (crear/colocar imagen sin cara)
  - backend/tests/fixtures/large_image.jpg (imagen >5MB para testing)
- **Descripcion:**
  - test_register_valid_face, test_register_no_face, test_register_low_quality
  - test_register_saves_embedding, test_register_saves_photo
  - test_register_multiple_faces
  - test_register_file_too_large, test_register_dimensions_too_large
- **Depende:** B5
- **Criterio:** pytest tests/test_register.py tests/test_image_validation.py -v todos pasan

---

## FASE 3: Reconocimiento y Asistencia

### B7. Reescribir POST /api/recognize — distancia coseno + asistencia
- **Archivos:** backend/main.py (modificar)
- **Descripcion:**
  - Recibir imagen
  - **Validar tamano de archivo: maximo 5MB.** Si excede, retornar error 413
  - **Validar dimensiones de imagen:** maximo 1920x1080 px para evitar colapsos de memoria
  - Extraer embedding con DeepFace
  - Comparar distancia coseno contra todos los estudiantes (threshold 0.4)
  - Si match: insertar en attendance (type='check-in', method='individual'), retornar {"name": ..., "distance": ..., "student_id": ...}
  - Si no match: retornar 404
- **Depende:** B1, B2
- **Criterio:** curl -X POST -F "file=@foto.jpg" localhost:8000/api/recognize retorna nombre si hay match; archivo >5MB retorna 413

### B8. Crear POST /api/recognize-group — grupal
- **Archivos:** backend/main.py (modificar)
- **Descripcion:**
  - Recibir imagen con multiples caras
  - **Validar tamano de archivo: maximo 5MB.** Si excede, retornar error 413
  - Para cada cara: extraer embedding + comparar
  - Retornar {"matches": [{"name": ..., "distance": ..., "bbox": ...}, ...]}
  - Registrar asistencia para cada match con type='check-in', method='group'
- **Depende:** B7
- **Criterio:** Foto grupal con 2 personas registradas retorna array de 2 matches

### B9. Implementar control de duplicados (5 min)
- **Archivos:** backend/main.py (modificar)
- **Descripcion:**
  - Antes de insertar en attendance, consultar ultimo registro del mismo student_id con type='check-in'
  - Si ultimo registro es < 5 minutos, no insertar
  - Retornar flag "duplicate": true en ese caso
- **Depende:** B7
- **Criterio:** Dos reconocimientos del mismo estudiante en 3 min: solo 1 registro en DB

### B10. Crear tests de FASE 3
- **Archivos:**
  - backend/tests/test_recognize.py (crear)
  - backend/tests/test_attendance.py (crear)
  - backend/tests/test_dedup.py (crear)
- **Descripcion:**
  - test_recognize_match_found, test_recognize_no_match, test_recognize_distance_threshold
  - test_recognize_group_multiple_faces
  - test_recognize_file_too_large
  - test_attendance_recorded (type='check-in', method='individual'), test_attendance_dedup_5min, test_attendance_dedup_after_window
  - test_attendance_links_student
- **Depende:** B7, B8, B9
- **Criterio:** pytest tests/test_recognize.py tests/test_attendance.py tests/test_dedup.py -v todos pasan

---

## FASE 4: Dashboard y Reportes

### B11. Crear GET /api/attendance — paginacion + filtros
- **Archivos:** backend/main.py (modificar)
- **Descripcion:**
  - Query params: date_from, date_to, student_id, page (default 1), limit (default 10)
  - JOIN con students para incluir nombre
  - Retornar {"records": [...], "total": ..., "page": ..., "pages": ...}
- **Depende:** B1
- **Criterio:** curl "localhost:8000/api/attendance?page=1&limit=5" retorna 5 registros max

### B12. Crear GET /api/students — listar estudiantes
- **Archivos:** backend/main.py (modificar)
- **Descripcion:**
  - Retornar lista de todos los estudiantes
  - {"students": [{"id": ..., "name": ..., "photo_path": ..., "created_at": ...}]}
- **Depende:** B1
- **Criterio:** curl localhost:8000/api/students retorna array de estudiantes

### B13. Crear GET /api/report/pdf — generacion de PDF
- **Archivos:** backend/main.py (modificar)
- **Descripcion:**
  - Query params: date_from, date_to
  - Generar PDF con fpdf2: tabla con fecha, hora, estudiante
  - Retornar como application/pdf
- **Depende:** B1
- **Criterio:** curl localhost:8000/api/report/pdf -o report.pdf genera PDF valido

### B14. Agregar dependencias a requirements.txt
- **Archivos:** backend/requirements.txt (modificar)
- **Agregar:**
  ```
  fpdf2
  pytest
  httpx
  python-dotenv
  ```
- **Criterio:** pip install -r requirements.txt instala sin errores

### B15. Crear tests de FASE 4
- **Archivos:**
  - backend/tests/test_attendance_endpoint.py (crear)
  - backend/tests/test_report_pdf.py (crear)
  - backend/tests/test_students_endpoint.py (crear)
- **Descripcion:**
  - test_get_attendance_empty, test_get_attendance_with_data (con type y method), test_get_attendance_pagination
  - test_get_attendance_filter_date, test_get_attendance_filter_student
  - test_report_pdf_returns_pdf, test_report_pdf_content, test_report_pdf_empty
  - test_get_students_list, test_get_students_fields
- **Depende:** B11, B12, B13
- **Criterio:** pytest tests/test_attendance_endpoint.py tests/test_report_pdf.py tests/test_students_endpoint.py -v todos pasan

### B16. Ejecutar suite completa de tests
- **Comando:**
  ```bash
  cd backend && pytest tests/ -v
  ```
- **Depende:** B4, B6, B10, B15
- **Criterio:** Todos los tests pasan, 0 failures

---

## FASE 5: Gestion de Estudiantes

### B17. Crear DELETE /api/students/{student_id} — eliminar estudiante
- **Archivos:** backend/main.py (modificar)
- **Descripcion:**
  - Recibir student_id como parametro de ruta
  - Verificar que el estudiante existe en la tabla students
  - Eliminar registro de la tabla students
  - Eliminar carpeta data/known_faces/{nombre}/ y todas sus imagenes
  - Retornar {"status": "deleted", "student_id": ..., "name": ...}
  - Error 404 si el estudiante no existe
- **Depende:** B1
- **Criterio:** curl -X DELETE localhost:8000/api/students/1 elimina estudiante y su carpeta; ID inexistente retorna 404

### B18. Crear tests de FASE 5
- **Archivos:**
  - backend/tests/test_student_delete.py (crear)
- **Descripcion:**
  - test_delete_student_success, test_delete_student_not_found
  - test_delete_student_removes_folder, test_delete_student_removes_attendance_records
- **Depende:** B17
- **Criterio:** pytest tests/test_student_delete.py -v todos pasan

---

## Resumen

| Fase | Tareas | Archivos a crear/modificar |
|------|--------|---------------------------|
| FASE 0 | B0 | .env.example, .env |
| FASE 1 | B1, B2, B3, B4 | app/db/database.py, app/core/ai_engine.py, main.py, tests/ |
| FASE 2 | B5, B6 | main.py, tests/ |
| FASE 3 | B7, B8, B9, B10 | main.py, tests/ |
| FASE 4 | B11, B12, B13, B14, B15, B16 | main.py, requirements.txt, tests/ |
| FASE 5 | B17, B18 | main.py, tests/ |
