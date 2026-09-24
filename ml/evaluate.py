"""
Step 3 of training: score the models on the two test sets they never saw.

  Rule test (541 images, rule labels): how well the served model learned the
      rules. This is the headline "top-1 accuracy": how often the model's
      first choice matches the label.
  Human test (60 images, labeled by eye): how well each model matches
      colour-and-mood judgements, for the stage-2 experiment.

It also scores the rules themselves on the human test. The stage-1 model can
only copy the rules, so that number is roughly its ceiling on human taste.
"""
from pathlib import Path

import numpy as np
import tensorflow as tf

from labeler import GENRES
from train import DATASET_PATH, HUMAN_MODEL_PATH, SERVED_MODEL_PATH


def accuracy(actual: np.ndarray, predicted: np.ndarray) -> str:
    return f"{np.mean(actual == predicted):.1%}"


def print_breakdown(title: str, actual: np.ndarray, predicted: np.ndarray) -> None:
    """Accuracy per genre, then a confusion matrix (rows = label, columns = model guess)."""
    print(f"\n{title}")
    for index, genre in enumerate(GENRES):
        mask = actual == index
        if mask.any():
            print(f"  {genre:10s} {np.mean(predicted[mask] == index):6.1%}  ({mask.sum()} images)")
    print(" " * 11 + " ".join(f"{g[:9]:>9s}" for g in GENRES))
    for row, genre in enumerate(GENRES):
        counts = [np.sum((actual == row) & (predicted == col)) for col in range(len(GENRES))]
        print(f"{genre:10s} " + " ".join(f"{c:9d}" for c in counts))


def predict(model_path: Path, features: np.ndarray) -> np.ndarray:
    return tf.keras.models.load_model(model_path).predict(features, verbose=0).argmax(axis=1)


def main():
    data = np.load(DATASET_PATH)
    has_humans = "y_human_test" in data and HUMAN_MODEL_PATH.exists()
    models = {"stage 1 (served)": SERVED_MODEL_PATH}
    if has_humans:
        models["stage 2 (human)"] = HUMAN_MODEL_PATH

    print(f"{'':18s} {'rule test':>10s} {'human test':>11s}")
    for name, path in models.items():
        rule_score = accuracy(data["y_test"], predict(path, data["x_test"]))
        human_score = accuracy(data["y_human_test"], predict(path, data["x_human_test"])) if has_humans else "-"
        print(f"{name:18s} {rule_score:>10s} {human_score:>11s}")
    if has_humans:
        print(f"{'the rules':18s} {'-':>10s} {accuracy(data['y_human_test'], data['y_human_test_rules']):>11s}")

    print_breakdown(f"stage 1 on the rule test ({len(data['y_test'])} images):",
                    data["y_test"], predict(SERVED_MODEL_PATH, data["x_test"]))
    if has_humans:
        print_breakdown(f"stage 2 on the human test ({len(data['y_human_test'])} images):",
                        data["y_human_test"], predict(HUMAN_MODEL_PATH, data["x_human_test"]))


if __name__ == "__main__":
    main()
