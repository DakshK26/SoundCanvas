"""
Step 1 of training: turn the raw images into labeled feature arrays.

For every image we compute its 8 features (features.py). Images in the rule
set get a label from labeler.py; images in the human set get the label we
picked by hand (label_images.py). See splits.py for which image goes where.

Saved to data/dataset.npz:
  x_train, y_train, x_val, y_val, x_test, y_test   rule-labeled splits
  x_tune, y_tune                                    150 hand-labeled, for fine-tuning
  x_human_test, y_human_test                        150 hand-labeled, for testing
  y_human_test_rules                                what the rules say for those 150
The human arrays are only written once all 300 images are hand-labeled.
"""
import numpy as np

from features import compute_features
from labeler import GENRES, label_genre
from splits import DATA_DIR, HUMAN_SET_SIZE, IMAGES_DIR, human_splits, load_human_labels, rule_splits

DATASET_PATH = DATA_DIR / "dataset.npz"


def features_for(names: list[str]) -> np.ndarray:
    return np.stack([compute_features(IMAGES_DIR / name) for name in names])


def rule_labels(features: np.ndarray) -> np.ndarray:
    return np.array([GENRES.index(label_genre(row)) for row in features])


def main():
    arrays = {}
    for split, names in rule_splits().items():
        arrays[f"x_{split}"] = features_for(names)
        arrays[f"y_{split}"] = rule_labels(arrays[f"x_{split}"])
        counts = np.bincount(arrays[f"y_{split}"], minlength=len(GENRES))
        print(f"rule {split:5s} {len(names):5d} images  " +
              "  ".join(f"{g}={c}" for g, c in zip(GENRES, counts)))

    human_labels = load_human_labels()
    if len(human_labels) < HUMAN_SET_SIZE:
        print(f"human set: {len(human_labels)}/{HUMAN_SET_SIZE} hand-labeled, so it is left out "
              f"(finish with label_images.py, then run this again)")
    else:
        tune, test = human_splits()
        for key, names in (("tune", tune), ("human_test", test)):
            arrays[f"x_{key}"] = features_for(names)
            arrays[f"y_{key}"] = np.array([GENRES.index(human_labels[name]) for name in names])
        arrays["y_human_test_rules"] = rule_labels(arrays["x_human_test"])
        print(f"human set: {len(tune)} fine-tune, {len(test)} test")

    np.savez(DATASET_PATH, **arrays)
    print(f"saved {DATASET_PATH}")


if __name__ == "__main__":
    main()
