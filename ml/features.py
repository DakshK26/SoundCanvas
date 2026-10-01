"""Python copy of cpp-core/src/ImageFeatures.cpp, used only at training time. build_dataset.py calls
compute_features to turn each photo in ml/data/raw_images into 8 numbers; in production cpp-core
does that, so the two must match or the model would be fed different numbers than it learned from.
tests/feature_parity/golden.json is the shared answer key both copies are tested against."""
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
# Our channels are 0..1 rather than 0-255, so multiplying by 255/100 makes "extremely colorful"
# land at 1.0. Same constant as COLORFULNESS_SCALE in the C++.
COLORFULNESS_SCALE = 255.0 / 100.0

# BT.601, same as the C++.
LUMA_WEIGHTS = (0.299, 0.587, 0.114)


def compute_features(path: str | Path) -> np.ndarray:
    # PIL stores every channel, HSV too, as 0-255, so dividing by 255 puts them all on 0..1.
    # The C++ divides each stb_image byte by 255.0 in the same way. convert("RGB") also turns
    # grayscale or transparent images into 3 channels, like the C++ asking stb_image for 3 channels.
    rgb_image = Image.open(path).convert("RGB")
    rgb = np.asarray(rgb_image, dtype=np.float32) / 255.0
    hsv = np.asarray(rgb_image.convert("HSV"), dtype=np.float32) / 255.0

    # The arrays are height x width x channel, so [:, :, 0] is every pixel's red value.
    # Taking the mean of a whole channel matches the C++ sumR / count.
    red, green, blue = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    avg_red, avg_green, avg_blue = red.mean(), green.mean(), blue.mean()
    brightness = (avg_red + avg_green + avg_blue) / 3.0

    # Hue is an angle around the colour wheel, and red sits at both ends of it. A proper average
    # would treat it as a circle, but this takes the plain mean of the numbers as a cheap shortcut.
    # A plain mean ignores the wrap at red (0.01 and 0.99 average to 0.5); the C++ does the same.
    # The C++ works hue and saturation out per pixel in hueAndSaturation(), written to give the
    # same values as PIL's convert("HSV"), then averages sumHue and sumSat.
    hue = hsv[:, :, 0].mean()
    saturation = hsv[:, :, 1].mean()

    # Colorfulness: how spread out the colors are on two opponent axes, plus a little for how far
    # the average color is from gray.
    # This is the Hasler and Suesstrunk (2003) measure. The eye compares colours in opposing pairs,
    # so each pixel is placed on a red against green axis and a yellow against blue axis. A gray
    # pixel scores 0 on both. A photo with many different colours has a wide spread on these axes.
    # The C++ builds the same two values per pixel (redGreen and yellowBlue).
    red_green = red - green
    yellow_blue = 0.5 * (red + green) - blue
    # numpy's std divides by the pixel count, the same as stdDev() in the C++, which gets it from
    # running sums instead. The C++ uses std::hypot for these square roots of summed squares.
    spread = np.sqrt(red_green.std() ** 2 + yellow_blue.std() ** 2)
    offset = np.sqrt(red_green.mean() ** 2 + yellow_blue.mean() ** 2)
    # 0.3 is the paper's weight for the offset. Capped at 1 so the feature stays in 0..1.
    colorfulness = min((spread + 0.3 * offset) * COLORFULNESS_SCALE, 1.0)

    # Contrast is how spread out the brightness of the pixels is. Each pixel becomes gray with the
    # BT.601 weights (green counts most because the eye is most sensitive to it), then its standard
    # deviation is taken, like stdDev(sumGray, sumGraySq, count) in the C++.
    gray = LUMA_WEIGHTS[0] * red + LUMA_WEIGHTS[1] * green + LUMA_WEIGHTS[2] * blue
    contrast = gray.std()

    # Same order as FEATURE_NAMES and ImageFeatures::toArray() in the C++.
    return np.array(
        [avg_red, avg_green, avg_blue, brightness, hue, saturation, colorfulness, contrast],
        dtype=np.float32,
    )
