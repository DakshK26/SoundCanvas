"""
makes golden.json = what ml/features.py gives for each test image

why: model trained on python features, but in prod C++ computes them. if they drift
the model gets inputs it never saw. so both get checked against this file:
  - ml/tests/test_features.py -> python still gives these exact numbers
  - cpp-core/tests/test_core.cpp -> C++ within TOLERANCE

only rerun if I change a feature extractor ON PURPOSE (from repo root):
  ml/.venv/Scripts/python tests/feature_parity/make_golden.py
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ml"))
from features import FEATURE_NAMES, compute_features  # noqa: E402

HERE = Path(__file__).parent
SYNTHETIC_DIR = HERE / "images"

# they can't match exactly: PIL rounds hue/sat to bytes (0-255) and decodes jpegs
# differently than stb_image. 0.01 = 1% of the range, way below what changes a prediction
# (actual max diff right now is ~0.003)
TOLERANCE = 0.01

SIZE = 64


def make_synthetic_images() -> None:
    """edge case pngs: gray (no colour), pure red/blue, gradient, noise"""
    SYNTHETIC_DIR.mkdir(exist_ok=True)
    rng = np.random.default_rng(42)
    ramp = np.linspace(0, 255, SIZE, dtype=np.uint8)
    images = {
        "gray.png": np.full((SIZE, SIZE, 3), 128, dtype=np.uint8),
        "red.png": np.tile(np.array([255, 0, 0], dtype=np.uint8), (SIZE, SIZE, 1)),
        "blue.png": np.tile(np.array([0, 0, 255], dtype=np.uint8), (SIZE, SIZE, 1)),
        "gradient.png": np.stack([np.tile(ramp, (SIZE, 1)), np.tile(ramp[:, None], (1, SIZE)),
                                  np.full((SIZE, SIZE), 60, dtype=np.uint8)], axis=2),
        "noise.png": rng.integers(0, 256, (SIZE, SIZE, 3), dtype=np.uint8),
    }
    for name, pixels in images.items():
        Image.fromarray(pixels, "RGB").save(SYNTHETIC_DIR / name)


def test_images() -> list[Path]:
    """synthetic pngs + the real example jpgs from the frontend (jpeg decoding is where they differ most)"""
    examples = sorted((ROOT / "frontend" / "public" / "examples").glob("*.jpg"))
    return sorted(SYNTHETIC_DIR.glob("*.png")) + examples


def main() -> None:
    make_synthetic_images()
    golden = {
        "feature_names": FEATURE_NAMES,
        "tolerance": TOLERANCE,
        "images": {
            path.relative_to(ROOT).as_posix(): [round(float(v), 6) for v in compute_features(path)]
            for path in test_images()
        },
    }
    (HERE / "golden.json").write_text(json.dumps(golden, indent=2) + "\n")
    print(f"wrote {len(golden['images'])} images to golden.json")


if __name__ == "__main__":
    main()
