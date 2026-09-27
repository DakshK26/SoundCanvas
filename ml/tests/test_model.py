"""
Tests for the trained model and the service that serves it. These need TensorFlow:
  pip install -r ml/requirements-dev.txt && python -m unittest discover -s ml/tests
"""
import sys
import unittest
from pathlib import Path

import numpy as np
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ml"))
from app import PredictRequest, model, predict  # noqa: E402
from build_dataset import assign_splits  # noqa: E402
from data_files import DATASET_PATH, load_labels, load_split  # noqa: E402
from genres import GENRES  # noqa: E402
from train import build_model  # noqa: E402

FEATURES = [0.5, 0.4, 0.3, 0.4, 0.2, 0.5, 0.4, 0.2]


class PredictEndpoint(unittest.TestCase):
    def test_returns_a_known_genre_and_a_probability(self):
        prediction = predict(PredictRequest(features=FEATURES))
        self.assertIn(prediction.genre, GENRES)
        self.assertGreaterEqual(prediction.confidence, 1 / len(GENRES))  # the top choice of 5
        self.assertLessEqual(prediction.confidence, 1)

    def test_rejects_the_wrong_number_of_features(self):
        for features in (FEATURES[:7], FEATURES + [0.5]):
            with self.subTest(count=len(features)), self.assertRaises(ValidationError):
                PredictRequest(features=features)

    def test_rejects_features_outside_0_to_1(self):
        for bad in (-0.1, 1.1, float("nan")):
            with self.subTest(value=bad), self.assertRaises(ValidationError):
                PredictRequest(features=[bad] + FEATURES[1:])


class TrainingData(unittest.TestCase):
    def test_dataset_matches_the_labels_and_the_split_rule(self):
        """Catches a dataset.csv that is stale after labels.csv or build_dataset.py changed."""
        splits = assign_splits(load_labels())
        with DATASET_PATH.open() as file:
            rows = [line.split(",")[:3] for line in file.read().splitlines()[1:]]
        self.assertEqual({image: split for image, split, _ in rows}, splits)
        self.assertEqual({image: genre for image, _, genre in rows}, load_labels())

    def test_splits_are_2400_train_and_600_test(self):
        x_train, _ = load_split("train")
        x_test, _ = load_split("test")
        self.assertEqual((len(x_train), len(x_test)), (2400, 600))


class TrainedModel(unittest.TestCase):
    def test_network_outputs_one_probability_per_genre(self):
        x_train, _ = load_split("train")
        probabilities = build_model(x_train, hidden_units=8, hidden_layers=1)(x_train[:4]).numpy()
        self.assertEqual(probabilities.shape, (4, len(GENRES)))
        np.testing.assert_allclose(probabilities.sum(axis=1), 1, rtol=1e-5)

    def test_committed_model_reproduces_its_reported_test_accuracy(self):
        """evaluate.ipynb and the README report 79.2%. A retrained or swapped model must update them."""
        x_test, y_test = load_split("test")
        accuracy = (model(x_test, training=False).numpy().argmax(axis=1) == y_test).mean()
        self.assertAlmostEqual(accuracy, 0.792, delta=0.001)


if __name__ == "__main__":
    unittest.main()
