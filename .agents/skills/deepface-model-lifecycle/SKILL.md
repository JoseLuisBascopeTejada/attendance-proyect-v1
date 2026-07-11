---
name: deepface-model-lifecycle
description: Use this skill whenever writing or editing code that loads a DeepFace model, extracts face embeddings, computes face-recognition matches, or handles FastAPI startup/warm-up events in the facial-recognition attendance backend. Trigger this even for small changes to app/core/ai_engine.py or to any endpoint (register, recognize, recognize-group) that calls DeepFace — this skill exists specifically to prevent the single most damaging performance bug in this class of project, which is reloading the ML model on every request instead of once at startup.
---

# DeepFace Model Lifecycle — Load Once, Never Per-Request

## The critical rule

**`DeepFace.build_model()` (or any equivalent model-loading call) must run
exactly once, at FastAPI application startup, and the loaded model object
must be kept in a module-level variable and reused for every request.**

If a model gets rebuilt inside a request handler, every single register or
recognize call will take 10-15 extra seconds. This is not a minor
inefficiency — it makes the API effectively unusable and is the most common
mistake when developers unfamiliar with DeepFace wire it into FastAPI.

### Wrong (do not do this)

```python
@app.post("/api/recognize")
async def recognize(file: UploadFile):
    model = DeepFace.build_model("Facenet")   # ❌ rebuilt every request
    embedding = DeepFace.represent(img, model=model)
    ...
```

### Right

```python
# app/core/ai_engine.py
from deepface import DeepFace

_model = None  # module-level, loaded once

def get_model():
    global _model
    if _model is None:
        _model = DeepFace.build_model("Facenet")
    return _model

def warm_up():
    """Run a dummy inference so the first real request isn't slow."""
    import numpy as np
    dummy = np.zeros((160, 160, 3), dtype=np.uint8)
    DeepFace.represent(dummy, model_name="Facenet", enforce_detection=False)

def extract_embedding(img_path: str):
    return DeepFace.represent(img_path, model_name="Facenet",
                               enforce_detection=True)[0]["embedding"]
```

```python
# main.py
from app.core.ai_engine import warm_up

@app.on_event("startup")
async def startup_event():
    init_db()
    warm_up()   # ✅ runs once, before the app accepts real traffic
```

## Checklist before finishing any task touching ai_engine.py or an
## endpoint that calls it

- [ ] Is the model held in a variable that lives at module scope (or
      `app.state`), not created inside a function that runs per-request?
- [ ] Is `warm_up()` wired into FastAPI's `startup` event, not called lazily
      on the first request?
- [ ] Does `warm_up()` use a small dummy image (160x160) so it's fast and
      doesn't require a real uploaded file?
- [ ] Does `extract_embedding()` reuse `get_model()` rather than loading its
      own copy?

## Face detection confidence vs. recognition distance — don't confuse them

These are two different numbers used at two different stages. Mixing them
up is a common source of subtle bugs:

| Stage | What it measures | Threshold | Used in |
|---|---|---|---|
| Face **detection** | How confident the detector is that a face exists in the image | `FACE_CONFIDENCE` (0.90) — higher is stricter | `/api/register` only |
| Face **recognition/matching** | Cosine distance between two embeddings | `THRESHOLD` (0.4) — **lower** is stricter, since it's a distance not a confidence | `/api/recognize`, `/api/recognize-group` |

A match is valid when `distance < THRESHOLD`. If you write
`distance > THRESHOLD` to mean "is a match," you've inverted the logic —
double check this every time you touch matching code, since "higher
threshold = stricter" is true for confidence but false for distance.

## Computing cosine distance correctly

```python
import numpy as np

def cosine_distance(a: list[float], b: list[float]) -> float:
    a, b = np.array(a), np.array(b)
    return 1 - (np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
```

Store embeddings as raw BLOBs (e.g. `np.array(embedding).tobytes()`) and
deserialize with `np.frombuffer(blob, dtype=np.float64)` — pick one dtype
and use it consistently for writes and reads, or comparisons will silently
produce garbage distances instead of raising an error.

## Multi-face images (register vs. recognize-group)

- `/api/register` expects exactly one face. If DeepFace detects multiple
  faces, use the one with the highest detection confidence — don't error
  out and don't silently pick the first one returned, since face order
  from the detector is not guaranteed to correlate with confidence.
- `/api/recognize-group` expects multiple faces and must process each one
  independently — extract an embedding per detected face, compare each
  against all students, and include a `bbox` per match in the response so
  the frontend can (eventually) draw boxes over recognized faces.

## Testing this layer without slow model loads

For `test_ai_engine.py`, load the model once in a `conftest.py` fixture
scoped at `session` level, not `function` level — otherwise every test that
touches the model reloads it and the test suite becomes as slow as the bug
this skill prevents.

```python
@pytest.fixture(scope="session")
def model():
    from app.core.ai_engine import get_model
    return get_model()
```