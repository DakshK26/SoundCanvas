"""
Tests for the Python side of the ML pipeline. Standard library only, so they
run without TensorFlow:  python -m unittest discover -s ml/tests
"""
import json
import re
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ml"))
from features import FEATURE_NAMES, compute_features  # noqa: E402
from labeler import GENRES, label_genre  # noqa: E402


class FeaturesMatchGolden(unittest.TestCase):
    """features.py must keep producing the numbers in tests/feature_parity/golden.json.
    cpp-core/tests/test_core.cpp checks the C++ copy against the same file."""

    def test_every_image(self):
        golden = json.loads((ROOT / "tests" / "feature_parity" / "golden.json").read_text())
        self.assertEqual(golden["feature_names"], FEATURE_NAMES)
        for path, expected in golden["images"].items():
            with self.subTest(image=path):
                np.testing.assert_allclose(compute_features(ROOT / path), expected, atol=1e-5)


class LabelerCoversEveryGenre(unittest.TestCase):
    """One hand-picked image description per rule branch, so a threshold edit that
    makes a genre unreachable is caught."""

    CASES = {
        # avg r, g, b, brightness, hue, saturation, colorfulness, contrast
        "EDM_DROP": [0.2, 0.1, 0.1, 0.15, 0.05, 0.8, 0.7, 0.3],   # dark and intense
        "CINEMATIC": [0.2, 0.2, 0.2, 0.2, 0.6, 0.1, 0.1, 0.1],    # dark and calm
        "HOUSE": [0.9, 0.8, 0.6, 0.8, 0.1, 0.7, 0.6, 0.25],      # bright and intense
        "EDM_CHILL": [0.8, 0.8, 0.9, 0.8, 0.6, 0.2, 0.2, 0.1],   # bright and calm
        "RETROWAVE": [0.5, 0.5, 0.6, 0.55, 0.6, 0.5, 0.3, 0.1],   # fairly bright, medium saturation
    }

    def test_each_genre_is_reachable(self):
        for genre, features in self.CASES.items():
            with self.subTest(genre=genre):
                self.assertEqual(label_genre(features), genre)

    def test_only_known_genres(self):
        rng = np.random.default_rng(0)
        for features in rng.random((500, 8)):
            self.assertIn(label_genre(features), GENRES)


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
