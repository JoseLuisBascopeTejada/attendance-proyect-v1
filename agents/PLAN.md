# PLAN.md — Sistema de Asistencia por Reconocimiento Facial

> **Este documento es la fuente de verdad de arquitectura y coordinación.**
> Las tareas detalladas viven en `BACKEND_TASKS.md` y `FRONTEND_TASKS.md`.
> Este PLAN.md ya NO contiene tareas paso a paso — solo define el contrato,
> las reglas técnicas y el orden de trabajo entre los dos agentes.

> ⚠️ **Nota de migración:** una versión anterior de este archivo tenía un
> esquema de base de datos y rutas de archivos distintas a las de
> `BACKEND_TASKS.md`. Esa versión queda obsoleta. **En caso de conflicto,
> `BACKEND_TASKS.md` y `FRONTEND_TASKS.md` tienen prioridad sobre este
> archivo para el detalle de cada tarea; este archivo tiene prioridad para
> el contrato de API y las reglas de arquitectura.**

---

## 1. Roles

| Agente | Responsabilidad | Fuente de tareas | No debe tocar |
|---|---|---|---|
| **Agente Backend** | FastAPI, SQLite, DeepFace, endpoints `/api/*`, tests con pytest | `BACKEND_TASKS.md` | `frontend/src/**` |
| **Agente Frontend** | React + Vite + TS, UI, consumo de la API | `FRONTEND_TASKS.md` | `backend/**` |

Cada agente trabaja **solo dentro de su carpeta** (`backend/` o `frontend/`).
El único punto de contacto entre ambos es el **contrato de API** (sección 3).
Si un agente necesita cambiar algo del contrato, debe actualizar la sección 3
de este archivo y avisar explícitamente — no asumir cambios silenciosos.

---

## 2. Stack tecnológico (fijo — no cambiar sin justificación)

### Backend
| Tecnología | Uso | Reglas |
|---|---|---|
| Python 3.11 | Runtime | Imagen base `python:3.11-slim` |
| FastAPI | Framework web | Todas las rutas bajo prefijo `/api/` (ver sección 3) |
| SQLite | Base de datos | Un solo archivo en `DB_PATH` (env var), sin ORM — SQL directo |
| DeepFace (modelo Facenet) | Embeddings faciales | Cargar una sola vez en memoria al iniciar (`app/core/ai_engine.py`), nunca por request |
| OpenCV / MTCNN | Detección de rostro | Confianza mínima 0.90 |
| fpdf2 | Generación de PDF | — |
| pytest + httpx | Testing | TestClient de FastAPI, DB en `:memory:` para tests |
| python-dotenv | Variables de entorno | `.env` NO se commitea, `.env.example` sí |

**Estructura de carpetas obligatoria (backend):**
```
backend/
  main.py
  requirements.txt
  .env / .env.example
  app/
    db/
      database.py       # get_connection(), init_db()
    core/
      ai_engine.py       # get_model(), extract_embedding(), warm_up()
  tests/
    conftest.py
    fixtures/
    test_*.py
```
❌ No usar `backend/db.py` ni `backend/models.py` sueltos en la raíz — eso
pertenece a una versión anterior y abandonada del plan.

### Frontend
| Tecnología | Uso | Reglas |
|---|---|---|
| React + Vite + TypeScript | Framework | Sin CRA, sin Next.js |
| react-webcam | Captura de cámara | Modo espejo solo visual (`scaleX(-1)`), la imagen enviada al backend va sin flip |
| axios | Cliente HTTP | Instancia única en `src/api/client.ts` |
| react-router-dom | Ruteo | `BrowserRouter`, rutas definidas en `App.tsx` |
| pnpm | Gestor de paquetes | `pnpm run lint` y `pnpm run build` deben pasar sin errores antes de dar una fase por cerrada |

**Estructura de carpetas obligatoria (frontend):**
```
frontend/
  src/
    api/
      client.ts
    components/
      WebcamCapture.tsx
    pages/
      Layout.tsx
      Dashboard.tsx
      Register.tsx
      Recognize.tsx
      RecognizeGroup.tsx
    App.tsx
    App.css
    index.css
```

### Infraestructura
- Docker Compose: backend en `:8000`, frontend (nginx) en `:3000`.
- `/app/data` **debe** estar montado como volumen (`./data:/app/data`) para
  persistir `attendance.db` y `known_faces/` entre reinicios.
- Backend: `libgl1` y `libglib2.0-0` instalados en la imagen (requeridos por OpenCV).
- Frontend: Dockerfile multi-stage — Node 22 para build, nginx para servir.
  `ENV CI=true` en el build para evitar prompts interactivos de pnpm.

---

## 3. Contrato de API (fuente de verdad — ambos agentes deben respetarlo)

**Base URL desde el frontend:** `http://localhost:8000/api`
**Prefijo obligatorio en el backend:** todas las rutas empiezan con `/api/`.

> ⚠️ Este es el punto de fricción más común entre los dos agentes: el
> backend expone `/api/register`, `/api/recognize`, etc. El frontend debe
> configurar su `baseURL` en `src/api/client.ts` como
> `http://localhost:8000/api` (CON `/api`), y luego llamar a las rutas
> relativas sin prefijo (`apiClient.post('/register', ...)`,
> `apiClient.get('/attendance', ...)`, etc.). Si alguno de los dos lados
> cambia el prefijo, debe actualizarse esta tabla primero.

| Método | Ruta (`/api/...`) | Body / Query | Respuesta éxito | Respuesta error |
|---|---|---|---|---|
| GET | `/db-status` | — | `{"status":"ok","db":"connected","tables":[...]}` | — |
| POST | `/register` | `multipart/form-data`: `file`, `name` | `{"id","name","status":"registered"}` | 400 sin cara · 413 tamaño/dimensión |
| POST | `/recognize` | `multipart/form-data`: `file` | `{"name","distance","student_id"}` | 404 sin match · 413 tamaño/dimensión |
| POST | `/recognize-group` | `multipart/form-data`: `file` | `{"matches":[{"name","distance","bbox"}]}` | 413 tamaño |
| GET | `/attendance` | `date_from, date_to, student_id, page, limit` | `{"records":[...],"total","page","pages"}` | — |
| GET | `/students` | — | `{"students":[{"id","name","photo_path","created_at"}]}` | — |
| DELETE | `/students/{id}` | — | `{"status":"deleted","student_id","name"}` | 404 |
| GET | `/report/pdf` | `date_from, date_to` | `application/pdf` | — |

**Reglas de validación compartidas (backend las implementa, frontend debe anticiparlas en la UI):**
- Tamaño máximo de imagen: 5MB → 413 con `{"detail": "File too large. Max 5MB allowed."}`
- Dimensiones máximas: 1920x1080px → 413 con `{"detail": "Image dimensions too large. Max 1920x1080px."}`
- Confianza mínima de detección de rostro: 0.90
- Threshold de distancia coseno para match: 0.4
- Deduplicación de asistencia: no repetir `check-in` del mismo estudiante en ventana de 5 minutos (el backend responde igual pero con `"duplicate": true`, no es un error)

---

## 4. Esquema de base de datos (definitivo)

```sql
CREATE TABLE students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,                    -- SIN UNIQUE: permite nombres repetidos
    embedding BLOB,
    photo_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    type TEXT CHECK(type IN ('check-in','check-out')),
    method TEXT CHECK(method IN ('individual','group')),
    FOREIGN KEY (student_id) REFERENCES students(id)
);
```

Este es el único esquema válido. Cualquier mención a `UNIQUE NOT NULL` en
`name` o a un campo `recognized_by` en `attendance` pertenece a una versión
anterior y debe ignorarse.

---

## 5. Variables de entorno (backend)

Definidas en `backend/.env` (no se commitea) / `backend/.env.example` (sí se commitea):

```
DB_PATH=/app/data/attendance.db
FACES_DIR=/app/data/known_faces
THRESHOLD=0.4
FACE_CONFIDENCE=0.90
MAX_FILE_SIZE_MB=5
MAX_IMAGE_WIDTH=1920
MAX_IMAGE_HEIGHT=1080
CORS_ORIGINS=*
```

El backend debe leer estas variables con `python-dotenv` / `os.getenv()`.
Ningún valor de estos (threshold, límites de tamaño, etc.) debe estar
hardcodeado en `main.py`.

---

## 6. Orden de ejecución y sincronización entre agentes

```
FASE 0  Backend: configuración (.env)
   ↓
FASE 1  Backend: DB + modelo IA + /api/db-status + tests
   ↓                                     Frontend: FASE 1 no tiene tareas —
   ↓                                     espera a que termine FASE 1 backend
FASE 2  Backend: /api/register       ←→  Frontend: cliente axios,
        + validaciones + tests            WebcamCapture, Register.tsx, router
   ↓                                              ↓
FASE 3  Backend: /api/recognize,     ←→  Frontend: Recognize.tsx,
        /api/recognize-group,               RecognizeGroup.tsx
        dedup + tests
   ↓                                              ↓
FASE 4  Backend: /api/attendance,    ←→  Frontend: Layout.tsx, Dashboard.tsx,
        /api/students, /api/report/pdf       PDF, tarjetas resumen, lint, build
   ↓
FASE 5  Backend: DELETE /api/students/{id} + tests
```

**Regla de sincronización:** el agente frontend puede *empezar* a construir
la UI de una fase (maquetado, formularios, estados de carga) usando el
contrato de la sección 3 como mock, sin esperar a que el backend termine esa
fase — pero la integración real (probar contra el backend corriendo) solo
se valida cuando ambos agentes reportan su fase como completa.

**Definición de "fase completa":**
- Backend: todos los tests de esa fase pasan (`pytest tests/ -v` para los
  archivos de esa fase).
- Frontend: `pnpm run lint` sin errores/warnings y flujo manual verificado
  contra el backend real (no mockeado) al menos una vez por fase.

---

## 7. Reglas generales para ambos agentes

1. **No inventar endpoints ni campos.** Si algo no está en la sección 3,
   coordínalo actualizando este archivo antes de implementarlo.
2. **No cambiar de stack.** No introducir ORMs, frameworks de estado
   (Redux, Zustand), CSS frameworks, ni cambiar SQLite por otro motor sin
   que se actualice explícitamente este PLAN.md.
3. **Un commit/PR por tarea** (`B1`, `F3`, etc.) cuando sea posible, para
   que el otro agente pueda rastrear qué se completó.
4. **No tocar archivos fuera de tu carpeta** (`backend/` o `frontend/`),
   excepto `docker-compose.yml` cuando la tarea lo requiera explícitamente
   (ej. volumen de datos en FASE 1).
5. **Los tests son parte de la tarea, no un extra.** Una tarea no se
   considera terminada si su fase de tests correspondiente no pasa.
6. **Ante ambigüedad, el contrato de la sección 3 gana** sobre supuestos
   individuales de cada agente.

---

## 8. Estructura de tests (backend)

```
backend/tests/
  __init__.py
  conftest.py              # fixtures: DB :memory:, TestClient, imágenes de prueba
  fixtures/
    face_known.jpg
    no_face.jpg
    large_image.jpg
  test_db.py                # FASE 1
  test_ai_engine.py         # FASE 1
  test_health.py            # FASE 1
  test_register.py          # FASE 2
  test_image_validation.py  # FASE 2
  test_recognize.py         # FASE 3
  test_attendance.py        # FASE 3
  test_dedup.py              # FASE 3
  test_attendance_endpoint.py  # FASE 4
  test_report_pdf.py           # FASE 4
  test_students_endpoint.py    # FASE 4
  test_student_delete.py       # FASE 5
```

Ejecución completa: `cd backend && pytest tests/ -v` → 0 failures antes de
dar por cerrado el proyecto (tarea B16).

---

## 9. Historial de cambios de este documento

- **v2 (actual):** Consolidado como documento de arquitectura/contrato,
  eliminando tareas paso a paso (ahora viven solo en `BACKEND_TASKS.md` /
  `FRONTEND_TASKS.md`). Corregido esquema de DB (sin `UNIQUE` en `name`,
  `type`/`method` en `attendance`). Corregidas rutas de archivos backend
  (`app/db/database.py`, `app/core/ai_engine.py`). Añadido contrato de API
  explícito con prefijo `/api/` para evitar mismatch con el frontend.
- **v1:** Versión original con tareas detalladas por fase (obsoleta,
  reemplazada por `BACKEND_TASKS.md` y `FRONTEND_TASKS.md`).