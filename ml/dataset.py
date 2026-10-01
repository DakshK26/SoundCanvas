"""Paths and CSV helpers shared by the scripts in ml/. build_dataset.py, train.py, app.py,
evaluate.ipynb and the tests import it, so every file in ml/data and ml/models is named in one place.
The fixed seed makes the split and the training repeatable."""
import csv
from pathlib import Path

import numpy as np

from genres import GENRES

# Paths are built from this file's folder, so the scripts work from any working directory.
DATA_DIR = Path(__file__).parent / "data"
IMAGES_DIR = DATA_DIR / "raw_images"
LABELS_PATH = DATA_DIR / "labels.csv"
DATASET_PATH = DATA_DIR / "dataset.csv"
MODEL_PATH = Path(__file__).parent / "models" / "genre_classifier.keras"
SEED = 42


# Every labeled photo, by filename. labels.csv has one row per name.
def all_images() -> list[str]:
    return sorted(path.name for path in IMAGES_DIR.glob("*.jpg"))


# image filename to one of the genre names.
def load_labels() -> dict[str, str]:
    with LABELS_PATH.open(newline="") as file:
        return {row["image"]: row["genre"] for row in csv.DictReader(file)}


def load_split(split: str) -> tuple[np.ndarray, np.ndarray]:
    """Features (N x 8) and genre indices for "train" or "test"."""
    # Columns: image, split, genre, then the 8 features.
    with DATASET_PATH.open(newline="") as file:
        reader = csv.reader(file)
        next(reader)  # skip the header row
        rows = [row for row in reader if row[1] == split]
    # float32 is the type the Keras model works in. Each genre name becomes its position in GENRES,
    # which is the integer label sparse cross-entropy in train.py expects.
    features = np.array([[float(value) for value in row[3:]] for row in rows], dtype=np.float32)
    genres = np.array([GENRES.index(row[2]) for row in rows])
    return features, genres
