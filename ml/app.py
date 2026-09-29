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
    features: list[Feature] = Field(min_length=8, max_length=8)


class PredictResponse(BaseModel):
    genre: GenreName
    confidence: float = Field(ge=0, le=1)


@app.post("/predict", response_model=PredictResponse)
def predict(request: PredictRequest) -> PredictResponse:
    probabilities = model(np.array([request.features], dtype=np.float32), training=False).numpy()[0]
    best = int(probabilities.argmax())
    return PredictResponse(genre=GENRES[best], confidence=float(probabilities[best]))


@app.get("/health")
def health() -> dict:
    return {"ok": True}
