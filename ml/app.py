"""
ml service - 8 features in, genre out.

worker sends the features cpp-core computed to POST /predict, gets back a genre name.
model loads once at import. tensorflow is slow to start -> ecs.tf gives ml a 60s health check grace period
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
    """8 features, each 0..1, same order as FEATURE_NAMES in features.py"""
    features: list[Feature] = Field(min_length=8, max_length=8)


class PredictResponse(BaseModel):
    """top genre + its softmax probability"""
    genre: GenreName
    confidence: float = Field(ge=0, le=1)


@app.post("/predict", response_model=PredictResponse)
def predict(request: PredictRequest) -> PredictResponse:
    """one image -> best genre. bad features get a 422 from pydantic before this even runs"""
    # learned: model(x) instead of model.predict(x). predict() sets up a whole batching
    # pipeline every call - fine for a dataset, slow (ms of overhead) for 1 row
    probabilities = model(np.array([request.features], dtype=np.float32), training=False).numpy()[0]
    best = int(probabilities.argmax())
    return PredictResponse(genre=GENRES[best], confidence=float(probabilities[best]))


@app.get("/health")
def health() -> dict:
    """for the ECS container health check"""
    return {"ok": True}
