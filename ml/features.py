"""Python copy of cpp-core/src/ImageFeatures.cpp for building the training set; tests/feature_parity checks they match."""
from pathlib import Path

import numpy as np
from PIL import Image

# Model input order, must match ImageFeatures.cpp.
FEATURE_NAMES = [
    "avg_red",       # 0..1
    "avg_green",     # 0..1
    "avg_blue",      # 0..1
    "brightness",    # mean of the three above
    "hue",           # mean HSV hue, 0..1
    "saturation",    # mean HSV saturation, 0..1
    "colorfulness",  # Hasler and Suesstrunk 2003, scaled to 0..1
    "contrast",      # std dev of grayscale, 0..0.5
]

# The paper's scale is 0-255, where about 100 is "extremely colorful".
COLORFULNESS_SCALE = 255.0 / 100.0

# BT.601, same as the C++.
LUMA_WEIGHTS = (0.299, 0.587, 0.114)


def compute_features(path: str | Path) -> np.ndarray:
    rgb_image = Image.open(path).convert("RGB")
    rgb = np.asarray(rgb_image, dtype=np.float32) / 255.0
    hsv = np.asarray(rgb_image.convert("HSV"), dtype=np.float32) / 255.0

    red, green, blue = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    avg_red, avg_green, avg_blue = red.mean(), green.mean(), blue.mean()
    brightness = (avg_red + avg_green + avg_blue) / 3.0

    # A plain mean ignores the wrap at red (0.01 and 0.99 average to 0.5); the C++ does the same.
    hue = hsv[:, :, 0].mean()
    saturation = hsv[:, :, 1].mean()

    red_green = red - green
    yellow_blue = 0.5 * (red + green) - blue
    spread = np.sqrt(red_green.std() ** 2 + yellow_blue.std() ** 2)
    offset = np.sqrt(red_green.mean() ** 2 + yellow_blue.mean() ** 2)
    colorfulness = min((spread + 0.3 * offset) * COLORFULNESS_SCALE, 1.0)

    gray = LUMA_WEIGHTS[0] * red + LUMA_WEIGHTS[1] * green + LUMA_WEIGHTS[2] * blue
    contrast = gray.std()

    return np.array(
        [avg_red, avg_green, avg_blue, brightness, hue, saturation, colorfulness, contrast],
        dtype=np.float32,
    )
