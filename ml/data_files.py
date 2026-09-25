"""
Where the ML data lives, shared by every script in this folder.

  data/raw_images/  3,000 Flickr8k photos (download_images.py)
  data/labels.csv         image, genre: one label per photo, by colour and mood (label_images.py)
  data/second_labels.csv  150 of the photos labeled again by a second labeler, to measure agreement
  data/dataset.csv        image, split, genre and the 8 features (build_dataset.py)
"""
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
    """Image filename -> genre, for every photo labeled so far."""
    if not LABELS_PATH.exists():
        return {}
    with LABELS_PATH.open(newline="") as file:
        return {row["image"]: row["genre"] for row in csv.DictReader(file)}


def save_labels(labels: dict[str, str]) -> None:
    with LABELS_PATH.open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["image", "genre"])
        writer.writerows(sorted(labels.items()))


def load_split(split: str) -> tuple[np.ndarray, np.ndarray]:
    """The features (one row of 8 per image) and genre indices of one split of dataset.csv."""
    with DATASET_PATH.open(newline="") as file:
        reader = csv.reader(file)
        next(reader)  # the header
        rows = [row for row in reader if row[1] == split]
    features = np.array([[float(value) for value in row[3:]] for row in rows], dtype=np.float32)
    genres = np.array([GENRES.index(row[2]) for row in rows])
    return features, genres
