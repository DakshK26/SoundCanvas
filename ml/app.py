"""The ml service, a FastAPI app run by uvicorn (see ml/Dockerfile). The worker's predictGenre() in
api/src/serviceClients.ts POSTs the 8 features from cpp-core to /predict and gets back the most
likely genre and its probability. The model loads once at start-up from
ml/models/genre_classifier.keras, which train.py writes."""
from typing import Annotated, Literal

import numpy as np
import tensorflow as tf
from fastapi import FastAPI
from pydantic import BaseModel, Field

from dataset import MODEL_PATH
from genres import GENRES

# Loaded at import time, so a missing or broken model stops the service from starting at all
# instead of failing on the first request.
app = FastAPI(title="SoundCanvas ml")
model = tf.keras.models.load_model(MODEL_PATH)

# FastAPI answers anything else with a 422, which the worker treats as a permanent failure.
# Feature is a float that pydantic checks is between 0 and 1. GenreName only allows the names in
# GENRES, so the response can't carry a genre the other services don't know.
Feature = Annotated[float, Field(ge=0, le=1)]
GenreName = Literal[tuple(GENRES)]


# The request body must be exactly 8 features, in FEATURE_NAMES order.
class PredictRequest(BaseModel):
    features: list[Feature] = Field(min_length=8, max_length=8)


class PredictResponse(BaseModel):
    genre: GenreName
    confidence: float = Field(ge=0, le=1)


@app.post("/predict", response_model=PredictResponse)
def predict(request: PredictRequest) -> PredictResponse:
    # One probability per genre from the softmax; the confidence is the top one.
    # The model takes a batch, so the features are wrapped as a batch of one row and [0] takes that
    # row back out. training=False is inference mode. The features stay raw because the
    # normalisation layer is inside the model.
    probabilities = model(np.array([request.features], dtype=np.float32), training=False).numpy()[0]
    # argmax is the position of the highest probability, which is also its position in GENRES.
    best = int(probabilities.argmax())
    return PredictResponse(genre=GENRES[best], confidence=float(probabilities[best]))


# ECS hits this; the model is already loaded, so a 200 means the service can predict.
@app.get("/health")
def health() -> dict:
    return {"ok": True}
