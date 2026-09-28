"""
data side tests - features, labels, splits. (no tensorflow needed for these)
  pip install -r ml/requirements-dev.txt && python -m unittest discover -s ml/tests
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
    """features.py vs tests/feature_parity/golden.json.
    test_core.cpp checks the C++ against the same file -> if both pass, python == C++"""

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
    """each genre split 80/20 by itself (fake labels w/ a rare genre to make sure)"""

    def test_each_genre_is_split_80_20(self):
        labels = {f"image_{i:05d}.jpg": GENRES[i % 3] if i % 50 else "RETROWAVE" for i in range(1000)}
        splits = assign_splits(labels)
        self.assertEqual(splits, assign_splits(labels))  # deterministic
        for genre in set(labels.values()):
            names = [image for image, g in labels.items() if g == genre]
            shares = [sum(splits[n] == split for n in names) / len(names)
                      for split in ("train", "test")]
            with self.subTest(genre=genre):
                np.testing.assert_allclose(shares, [0.8, 0.2], atol=0.03)


class GenreNamesAgree(unittest.TestCase):
    """same 5 names in 4 services / 3 languages. regex'ing the source is hacky but it works"""

    def names_in(self, relative_path: str, pattern: str) -> set[str]:
        text = (ROOT / relative_path).read_text()
        return set(re.findall(pattern, text, re.MULTILINE))

    def test_all_services_use_the_same_names(self):
        expected = set(GENRES)
        schema = (ROOT / "gateway/src/schema.ts").read_text()
        self.assertEqual(set(re.findall(r'"([A-Z_]+)"', re.search(r"GENRES = \[([^\]]*)\]", schema).group(1))), expected)
        self.assertEqual(self.names_in("cpp-core/src/GenreTemplate.cpp", r'name == "([A-Z_]+)"'), expected)
        self.assertEqual(self.names_in("audio-producer/drums.py", r'^\s+"([A-Z_]+)": Kit\('), expected)
        self.assertEqual(self.names_in("audio-producer/mixer.py", r'^\s+"([A-Z_]+)": Mix\('), expected)


if __name__ == "__main__":
    unittest.main()
