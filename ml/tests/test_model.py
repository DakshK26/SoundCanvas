"""Checks the serving side: /predict's input rules, the dataset file, and that the committed model
still gets its reported accuracy. Importing app loads ml/models/genre_classifier.keras, so the
model has to be present for these to run."""
import sys
import unittest
from pathlib import Path

import numpy as np
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ml"))
from app import PredictRequest, model, predict  # noqa: E402
from build_dataset import assign_splits  # noqa: E402
from dataset import DATASET_PATH, load_labels, load_split  # noqa: E402
from genres import GENRES  # noqa: E402
from train import build_model  # noqa: E402

# Any valid set of 8 features in 0..1.
FEATURES = [0.5, 0.4, 0.3, 0.4, 0.2, 0.5, 0.4, 0.2]


class PredictEndpoint(unittest.TestCase):
    def test_returns_a_known_genre_and_a_probability(self):
        """Protects the /predict response in ml/app.py: a genre from ml/genres.py and a confidence
        that is a probability. The top of 4 probabilities that sum to 1 can't be below 1/4."""
        prediction = predict(PredictRequest(features=FEATURES))
        self.assertIn(prediction.genre, GENRES)
        self.assertGreaterEqual(prediction.confidence, 1 / len(GENRES))
        self.assertLessEqual(prediction.confidence, 1)

    def test_rejects_the_wrong_number_of_features(self):
        """Protects the exactly-8-features rule on PredictRequest in ml/app.py."""
        for features in (FEATURES[:7], FEATURES + [0.5]):
            with self.subTest(count=len(features)), self.assertRaises(ValidationError):
                PredictRequest(features=features)

    def test_rejects_features_outside_0_to_1(self):
        """Protects the 0..1 range on Feature in ml/app.py. NaN must be rejected too, not passed to
        the model."""
        for bad in (-0.1, 1.1, float("nan")):
            with self.subTest(value=bad), self.assertRaises(ValidationError):
                PredictRequest(features=[bad] + FEATURES[1:])


class TrainingData(unittest.TestCase):
    def test_dataset_matches_the_labels_and_the_split_rule(self):
        """Protects ml/data/dataset.csv from going stale: its split and genre columns must still
        match what assign_splits() in ml/build_dataset.py and ml/data/labels.csv give today."""
        splits = assign_splits(load_labels())
        # Skip the header, then keep the first three columns: image, split, genre.
        with DATASET_PATH.open() as file:
            rows = [line.split(",")[:3] for line in file.read().splitlines()[1:]]
        self.assertEqual({image: split for image, split, _ in rows}, splits)
        self.assertEqual({image: genre for image, _, genre in rows}, load_labels())

    def test_splits_are_2362_train_and_591_test(self):
        """Protects the split sizes that load_split() in ml/dataset.py returns from dataset.csv."""
        x_train, _ = load_split("train")
        x_test, _ = load_split("test")
        self.assertEqual((len(x_train), len(x_test)), (2362, 591))


class TrainedModel(unittest.TestCase):
    def test_network_outputs_one_probability_per_genre(self):
        """Protects the output layer from build_model() in ml/train.py: one probability per genre
        for each row, adding up to 1. A tiny network is enough, since only the shape is checked."""
        x_train, _ = load_split("train")
        probabilities = build_model(x_train, hidden_units=8, hidden_layers=1)(x_train[:4]).numpy()
        self.assertEqual(probabilities.shape, (4, len(GENRES)))
        np.testing.assert_allclose(probabilities.sum(axis=1), 1, rtol=1e-5)

    def test_committed_model_reproduces_its_reported_test_accuracy(self):
        """Committed model must still hit the reported 80.9%.

        Protects ml/models/genre_classifier.keras, the model app.py serves, against being replaced
        or the test split changing without the figure from evaluate.ipynb being updated."""
        # argmax(axis=1) picks the top genre for each row; comparing with the true labels and taking
        # the mean gives the share that are right.
        x_test, y_test = load_split("test")
        accuracy = (model(x_test, training=False).numpy().argmax(axis=1) == y_test).mean()
        self.assertAlmostEqual(accuracy, 0.809, delta=0.001)


if __name__ == "__main__":
    unittest.main()
