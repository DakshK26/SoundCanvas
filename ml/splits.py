"""
Which image goes where. Shared by label_images.py and build_dataset.py so they agree.

The 3,000 images are split once, with fixed seeds:

  300 human set, labeled by eye in label_images.py
      70% fine-tune (210): teach the model human taste
      10% validation (30): decide when to stop fine-tuning
      20% human test (60): never trained on; the "does it match people?" score
  2,700 rule set, labeled by labeler.py
      70% train, 10% validation (for choosing settings), 20% test

The human set is taken out first, so no hand-labeled image is ever trained on
with a rule label.
"""
import csv
import random
from pathlib import Path

import numpy as np

DATA_DIR = Path(__file__).parent / "data"
IMAGES_DIR = DATA_DIR / "raw_images"
HUMAN_LABELS_PATH = DATA_DIR / "human_labels.csv"

SEED = 42
HUMAN_SET_SIZE = 300  # ~18 minutes of labeling
HUMAN_TUNE_SIZE = 210  # 70%
HUMAN_VALIDATION_SIZE = 30  # 10%; the remaining 60 (20%) are the human test set
RULE_TRAIN_FRACTION = 0.7
RULE_VALIDATION_FRACTION = 0.1  # the remaining 20% is the rule test set


def all_images() -> list[str]:
    return sorted(path.name for path in IMAGES_DIR.glob("*.jpg"))


def human_set() -> list[str]:
    """The images to hand-label: a fixed random sample, identical on every run."""
    return sorted(random.Random(SEED).sample(all_images(), HUMAN_SET_SIZE))


def human_splits() -> tuple[list[str], list[str], list[str]]:
    """(fine-tune, validation, test) parts of the human set."""
    shuffled = list(human_set())
    random.Random(SEED).shuffle(shuffled)
    val_end = HUMAN_TUNE_SIZE + HUMAN_VALIDATION_SIZE
    return (sorted(shuffled[:HUMAN_TUNE_SIZE]), sorted(shuffled[HUMAN_TUNE_SIZE:val_end]),
            sorted(shuffled[val_end:]))


def rule_splits() -> dict[str, list[str]]:
    """Train, validation and test lists from the images outside the human set."""
    reserved = set(human_set())
    names = [name for name in all_images() if name not in reserved]
    order = np.random.default_rng(SEED).permutation(len(names))
    train_end = int(RULE_TRAIN_FRACTION * len(names))
    val_end = train_end + int(RULE_VALIDATION_FRACTION * len(names))
    return {
        "train": [names[i] for i in order[:train_end]],
        "val": [names[i] for i in order[train_end:val_end]],
        "test": [names[i] for i in order[val_end:]],
    }


def load_human_labels() -> dict[str, str]:
    """Image filename -> genre for every image hand-labeled so far."""
    if not HUMAN_LABELS_PATH.exists():
        return {}
    with HUMAN_LABELS_PATH.open(newline="") as file:
        return {row["image"]: row["genre"] for row in csv.DictReader(file)}


def save_human_labels(labels: dict[str, str]) -> None:
    with HUMAN_LABELS_PATH.open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["image", "genre"])
        writer.writerows(sorted(labels.items()))
