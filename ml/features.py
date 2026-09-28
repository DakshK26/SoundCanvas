"""
python version of cpp-core/src/ImageFeatures.cpp

only used offline to build the training set. in prod cpp-core computes the features,
so NOTE: both have to give the same 8 numbers in the same order or the model gets
inputs it never saw in training. tests/feature_parity/ checks they agree.
"""
from pathlib import Path

import numpy as np
from PIL import Image

# order = model input order, don't reorder!!
FEATURE_NAMES = [
    "avg_red",       # 0..1
    "avg_green",     # 0..1
    "avg_blue",      # 0..1
    "brightness",    # avg of the 3 above
    "hue",           # mean hsv hue 0..1 (0 red, .33 green, .66 blue)
    "saturation",    # mean hsv saturation 0..1
    "colorfulness",  # Hasler & Suesstrunk 2003, scaled to 0..1
    "contrast",      # std dev of grayscale, 0..0.5
]

# paper's scale is 0-255 where ~100 = "extremely colorful" -> *255/100 gets us ~0..1
COLORFULNESS_SCALE = 255.0 / 100.0

# BT.601 luma weights, same as the C++
LUMA_WEIGHTS = (0.299, 0.587, 0.114)


def compute_features(path: str | Path) -> np.ndarray:
    """image file -> 8 features"""
    rgb_image = Image.open(path).convert("RGB")
    rgb = np.asarray(rgb_image, dtype=np.float32) / 255.0
    hsv = np.asarray(rgb_image.convert("HSV"), dtype=np.float32) / 255.0

    red, green, blue = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    avg_red, avg_green, avg_blue = red.mean(), green.mean(), blue.mean()
    brightness = (avg_red + avg_green + avg_blue) / 3.0

    # gotcha: plain mean of an angle, so half 0.01 red + half 0.99 red averages to 0.5 (cyan).
    # C++ does the same so they still match. TODO(maybe): circular mean in both
    hue = hsv[:, :, 0].mean()
    saturation = hsv[:, :, 1].mean()

    # opponent color axes: red-green and yellow-blue
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
