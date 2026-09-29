"""Paths and CSV helpers shared by the scripts in ml/."""
import csv
from pathlib import Path

import numpy as np

from genres import GENRES

DATA_DIR = Path(__file__).parent / "data"
IMAGES_DIR = DATA_DIR / "raw_images"
LABELS_PATH = DATA_DIR / "labels.csv"
DATASET_PATH = DATA_DIR / "dataset.csv"
MODEL_PATH = Path(__file__).parent / "models" / "genre_classifier.keras"
SEED = 42


def all_images() -> list[str]:
    return sorted(path.name for path in IMAGES_DIR.glob("*.jpg"))


def load_labels() -> dict[str, str]:
    with LABELS_PATH.open(newline="") as file:
        return {row["image"]: row["genre"] for row in csv.DictReader(file)}


def load_split(split: str) -> tuple[np.ndarray, np.ndarray]:
    """Features (N x 8) and genre indices for "train" or "test"."""
    with DATASET_PATH.open(newline="") as file:
        reader = csv.reader(file)
        next(reader)
        rows = [row for row in reader if row[1] == split]
    features = np.array([[float(value) for value in row[3:]] for row in rows], dtype=np.float32)
    genres = np.array([GENRES.index(row[2]) for row in rows])
    return features, genres
