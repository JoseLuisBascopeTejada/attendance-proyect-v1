import os

import numpy as np
from deepface import DeepFace

_model = None


def get_detector_backend() -> str:
    return os.getenv("DETECTOR_BACKEND", "retinaface")


# Fraction of total image area a face must occupy to be accepted.
# Tunable via MIN_FACE_AREA_RATIO env var; flag for real-world adjustment.
MIN_FACE_AREA_RATIO = float(os.getenv("MIN_FACE_AREA_RATIO", "0.05"))


def get_model():
    global _model
    if _model is None:
        _model = DeepFace.build_model("Facenet")
    return _model


def warm_up():
    get_model()
    detector = get_detector_backend()
    dummy = np.zeros((480, 640, 3), dtype=np.uint8)
    DeepFace.extract_faces(img_path=dummy, detector_backend=detector, enforce_detection=False)
    DeepFace.represent(img_path=dummy, model_name="Facenet", detector_backend="skip")


def extract_embedding(img_path: str):
    get_model()
    detector = get_detector_backend()
    return DeepFace.represent(
        img_path=img_path,
        model_name="Facenet",
        detector_backend=detector,
        enforce_detection=True,
    )[0]["embedding"]


def cosine_distance(a: list[float], b: list[float]) -> float:
    a_np, b_np = np.array(a), np.array(b)
    return 1 - (np.dot(a_np, b_np) / (np.linalg.norm(a_np) * np.linalg.norm(b_np)))
