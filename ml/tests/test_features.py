"""Checks the training data side: features match the golden file, every photo has a label, the
split is stratified, and all services use the same genre names."""
import json
import re
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ml"))
from build_dataset import assign_splits  # noqa: E402
from dataset import all_images, load_labels  # noqa: E402
from features import FEATURE_NAMES, compute_features  # noqa: E402
from genres import GENRES  # noqa: E402


class FeaturesMatchGolden(unittest.TestCase):
    """test_core.cpp checks the C++ against the same golden.json."""

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
    def test_each_genre_is_split_80_20(self):
        # A made-up set with one rare genre, so the split still holds for a small class.
        rare = GENRES[-1]
        labels = {f"image_{i:05d}.jpg": GENRES[i % (len(GENRES) - 1)] if i % 50 else rare for i in range(1000)}
        splits = assign_splits(labels)
        self.assertEqual(splits, assign_splits(labels))
        for genre in set(labels.values()):
            names = [image for image, g in labels.items() if g == genre]
            shares = [sum(splits[n] == split for n in names) / len(names)
                      for split in ("train", "test")]
            with self.subTest(genre=genre):
                np.testing.assert_allclose(shares, [0.8, 0.2], atol=0.03)


class GenreNamesAgree(unittest.TestCase):
    def names_in(self, relative_path: str, pattern: str) -> set[str]:
        text = (ROOT / relative_path).read_text()
        return set(re.findall(pattern, text, re.MULTILINE))

    def test_all_services_use_the_same_names(self):
        # Reads each service's source as text and pulls out its genre names.
        expected = set(GENRES)
        schema = (ROOT / "api/src/schema.ts").read_text()
        self.assertEqual(set(re.findall(r'"([A-Z_]+)"', re.search(r"GENRES = \[([^\]]*)\]", schema).group(1))), expected)
        self.assertEqual(self.names_in("cpp-core/src/GenreTemplate.cpp", r'name == "([A-Z_]+)"'), expected)
        self.assertEqual(self.names_in("audio-producer/drums.py", r'^\s+"([A-Z_]+)": Kit\('), expected)
        self.assertEqual(self.names_in("audio-producer/mixer.py", r'^\s+"([A-Z_]+)": Mix\('), expected)


if __name__ == "__main__":
    unittest.main()
