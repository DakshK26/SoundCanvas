"""
Image features for training the genre model.

This is the Python copy of cpp-core/src/ImageFeatures.cpp. It is used only
offline, to build the training dataset. At runtime cpp-core computes the
features, so both versions must return the same 8 numbers in the same order.
"""
from pathlib import Path

import numpy as np
from PIL import Image

# The order of this list is the order of the model's inputs.
FEATURE_NAMES = [
    "avg_red",       # mean red channel, 0 to 1
    "avg_green",     # mean green channel, 0 to 1
    "avg_blue",      # mean blue channel, 0 to 1
    "brightness",    # mean of the three channel averages, 0 to 1
    "hue",           # mean HSV hue, 0 to 1 (0 = red, 0.33 = green, 0.66 = blue)
    "saturation",    # mean HSV saturation, 0 to 1
    "colorfulness",  # Hasler and Suesstrunk (2003) colorfulness, scaled to 0 to 1
    "contrast",      # standard deviation of grayscale brightness, 0 to 0.5
]

# Hasler and Suesstrunk define colorfulness on 0-255 pixel values, where about
# 100 already means "extremely colorful". We scale by that so the result is 0 to 1.
COLORFULNESS_SCALE = 255.0 / 100.0

# ITU-R BT.601 luma weights: how bright each channel looks to the human eye.
LUMA_WEIGHTS = (0.299, 0.587, 0.114)


def compute_features(path: str | Path) -> np.ndarray:
    """Return the 8 image features for one image file."""
    rgb_image = Image.open(path).convert("RGB")
    rgb = np.asarray(rgb_image, dtype=np.float32) / 255.0
    hsv = np.asarray(rgb_image.convert("HSV"), dtype=np.float32) / 255.0

    red, green, blue = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    avg_red, avg_green, avg_blue = red.mean(), green.mean(), blue.mean()
    brightness = (avg_red + avg_green + avg_blue) / 3.0

    hue = hsv[:, :, 0].mean()
    saturation = hsv[:, :, 1].mean()

    # Colorfulness uses two "opponent" color axes: red vs green, and yellow vs blue.
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
