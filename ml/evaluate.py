"""
Step 3 of training: measure the model on the held-out test split.

The test images were never used for training or for choosing settings, so
this is the honest score. It prints overall top-1 accuracy (how often the
model's first choice matches the rule label), accuracy per genre, and a
confusion matrix.
"""
from pathlib import Path

import numpy as np
import tensorflow as tf

from labeler import GENRES

DATASET_PATH = Path(__file__).parent / "data" / "dataset.npz"
MODEL_PATH = Path(__file__).parent / "models" / "genre_classifier.keras"


def main():
    """Print test accuracy, per-genre accuracy, and the confusion matrix."""
    data = np.load(DATASET_PATH)
    model = tf.keras.models.load_model(MODEL_PATH)

    predicted = model.predict(data["x_test"], verbose=0).argmax(axis=1)
    actual = data["y_test"]

    print(f"Test images: {len(actual)}")
    print(f"Top-1 accuracy: {np.mean(predicted == actual):.1%}\n")

    print("Accuracy per genre:")
    for index, genre in enumerate(GENRES):
        mask = actual == index
        print(f"  {genre:10s} {np.mean(predicted[mask] == index):6.1%}  ({mask.sum()} images)")

    # Rows are the rule label, columns are the model's guess.
    print("\nConfusion matrix (rows = rule label, columns = model guess):")
    print(" " * 11 + " ".join(f"{g[:9]:>9s}" for g in GENRES))
    for row, genre in enumerate(GENRES):
        counts = [np.sum((actual == row) & (predicted == col)) for col in range(len(GENRES))]
        print(f"{genre:10s} " + " ".join(f"{c:9d}" for c in counts))


if __name__ == "__main__":
    main()
