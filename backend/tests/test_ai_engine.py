import numpy as np


def test_model_load(model):
    assert model is not None


def test_warm_up():
    from app.core.ai_engine import warm_up

    warm_up()
