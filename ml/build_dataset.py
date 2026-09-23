"""
Step 1 of training: turn the raw images into a labeled dataset.

For each image in data/raw_images we compute its 8 features and a genre label
from the rules in labeler.py. We shuffle once with a fixed seed and split
70% train, 10% validation, 20% test. The result is saved to data/dataset.npz.
"""
from pathlib import Path

import numpy as np

from features import compute_features
from labeler import GENRES, label_genre

IMAGES_DIR = Path(__file__).parent / "data" / "raw_images"
DATASET_PATH = Path(__file__).parent / "data" / "dataset.npz"
SEED = 42
TRAIN_FRACTION = 0.7
VALIDATION_FRACTION = 0.1  # the remaining 20% is the test set


def main():
    """Build and save the train, validation, and test splits."""
    paths = sorted(IMAGES_DIR.glob("*.jpg"))
    features = np.stack([compute_features(path) for path in paths])
    labels = np.array([GENRES.index(label_genre(row)) for row in features])

    order = np.random.default_rng(SEED).permutation(len(paths))
    train_end = int(TRAIN_FRACTION * len(order))
    val_end = train_end + int(VALIDATION_FRACTION * len(order))
    splits = {
        "train": order[:train_end],
        "val": order[train_end:val_end],
        "test": order[val_end:],
    }

    arrays = {}
    for name, indices in splits.items():
        arrays[f"x_{name}"] = features[indices]
        arrays[f"y_{name}"] = labels[indices]
    np.savez(DATASET_PATH, **arrays)

    print(f"{len(paths)} images -> train {len(splits['train'])}, "
          f"val {len(splits['val'])}, test {len(splits['test'])}")
    for index, genre in enumerate(GENRES):
        print(f"  {genre:10s} {np.sum(labels == index)} images")


if __name__ == "__main__":
    main()
