"""
ml service: predicts a genre from 8 image features.

The worker calls POST /predict with the features cpp-core computed, and gets
back the genre name the composer should use. The model is loaded once at startup.
"""
from pathlib import Path

import numpy as np
import tensorflow as tf
from fastapi import FastAPI
from pydantic import BaseModel, Field

from labeler import GENRES

MODEL_PATH = Path(__file__).parent / "models" / "genre_classifier.keras"

app = FastAPI(title="SoundCanvas ml")
model = tf.keras.models.load_model(MODEL_PATH)


class PredictRequest(BaseModel):
    """The 8 features, in the order listed in features.py."""
    features: list[float] = Field(min_length=8, max_length=8)


class PredictResponse(BaseModel):
    """The most likely genre and the model's probability for it."""
    genre: str
    confidence: float


@app.post("/predict", response_model=PredictResponse)
def predict(request: PredictRequest) -> PredictResponse:
    """Return the most likely genre for one image."""
    probabilities = model.predict(np.array([request.features]), verbose=0)[0]
    best = int(probabilities.argmax())
    return PredictResponse(genre=GENRES[best], confidence=float(probabilities[best]))


@app.get("/health")
def health() -> dict:
    """Used by the load balancer to check the service is up."""
    return {"ok": True}
