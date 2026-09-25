"""
Tests for the Python side of the ML pipeline. They run without TensorFlow:
  pip install numpy pillow scikit-learn && python -m unittest discover -s ml/tests
"""
import json
import re
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ml"))
from build_dataset import assign_splits  # noqa: E402
from data_files import all_images, load_labels  # noqa: E402
from features import FEATURE_NAMES, compute_features  # noqa: E402
from genres import GENRES  # noqa: E402


class FeaturesMatchGolden(unittest.TestCase):
    """features.py must keep producing the numbers in tests/feature_parity/golden.json.
    cpp-core/tests/test_core.cpp checks the C++ copy against the same file."""

    def test_every_image(self):
        golden = json.loads((ROOT / "tests" / "feature_parity" / "golden.json").read_text())
        self.assertEqual(golden["feature_names"], FEATURE_NAMES)
        for path, expected in golden["images"].items():
            with self.subTest(image=path):
                np.testing.assert_allclose(compute_features(ROOT / path), expected, atol=1e-5)


class LabelsAreComplete(unittest.TestCase):
    def test_every_photo_has_one_known_genre(self):
        labels = load_labels()
        self.assertEqual(sorted(labels), all_images())
        self.assertLessEqual(set(labels.values()), set(GENRES))


class SplitsAreStratified(unittest.TestCase):
    """Each genre must be divided 70/10/20 on its own, with no photo in two splits."""

    def test_each_genre_is_split_70_10_20(self):
        labels = {f"image_{i:05d}.jpg": GENRES[i % 3] if i % 50 else "RETROWAVE" for i in range(1000)}
        splits = assign_splits(labels)
        self.assertEqual(splits, assign_splits(labels))  # the same every run
        for genre in set(labels.values()):
            names = [image for image, g in labels.items() if g == genre]
            shares = [sum(splits[n] == split for n in names) / len(names)
                      for split in ("train", "validation", "test")]
            with self.subTest(genre=genre):
                np.testing.assert_allclose(shares, [0.7, 0.1, 0.2], atol=0.03)


class GenreNamesAgree(unittest.TestCase):
    """The five genre names are a contract between four services in three languages."""

    def names_in(self, relative_path: str, pattern: str) -> set[str]:
        text = (ROOT / relative_path).read_text()
        return set(re.findall(pattern, text, re.MULTILINE))

    def test_all_services_use_the_same_names(self):
        expected = set(GENRES)
        schema = (ROOT / "gateway/src/schema.ts").read_text()
        self.assertEqual(set(re.search(r"enum Genre \{([^}]*)\}", schema).group(1).split()), expected)
        self.assertEqual(self.names_in("cpp-core/src/GenreTemplate.cpp", r'name == "([A-Z_]+)"'), expected)
        self.assertEqual(self.names_in("audio-producer/drums.py", r'^\s+"([A-Z_]+)": Kit\('), expected)
        self.assertEqual(self.names_in("audio-producer/mixer.py", r'^\s+"([A-Z_]+)": Mix\('), expected)


if __name__ == "__main__":
    unittest.main()
