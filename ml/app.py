"""
ml service: predicts a genre from 8 image features.

The worker calls POST /predict with the features cpp-core computed, and gets
back the genre name the composer should use. The model is loaded once at startup.
"""
from typing import Annotated, Literal

import numpy as np
import tensorflow as tf
from fastapi import FastAPI
from pydantic import BaseModel, Field

from data_files import MODEL_PATH
from genres import GENRES

app = FastAPI(title="SoundCanvas ml")
model = tf.keras.models.load_model(MODEL_PATH)

Feature = Annotated[float, Field(ge=0, le=1)]
GenreName = Literal[tuple(GENRES)]


class PredictRequest(BaseModel):
    """The 8 features, each 0 to 1, in the order listed in features.py."""
    features: list[Feature] = Field(min_length=8, max_length=8)


class PredictResponse(BaseModel):
    """The most likely genre and the model's probability for it."""
    genre: GenreName
    confidence: float = Field(ge=0, le=1)


@app.post("/predict", response_model=PredictResponse)
def predict(request: PredictRequest) -> PredictResponse:
    """Return the most likely genre for one image. FastAPI answers 422 to invalid features."""
    # Calling the model directly skips model.predict()'s batching machinery, which
    # costs milliseconds per call and is built for datasets, not one row.
    probabilities = model(np.array([request.features], dtype=np.float32), training=False).numpy()[0]
    best = int(probabilities.argmax())
    return PredictResponse(genre=GENRES[best], confidence=float(probabilities[best]))


@app.get("/health")
def health() -> dict:
    """Used by the ECS container health check."""
    return {"ok": True}
