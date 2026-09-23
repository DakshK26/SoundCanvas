"""
Rule-based genre labeler.

No public dataset says "this photo sounds like House", and hand-labeling
thousands of images was not practical, so these hand-written rules label the
2,700 rule-set images. The stage-1 model learns to reproduce them, which is why
its test accuracy means agreement with these rules. To check the rules against
real taste, we hand-labeled 300 other images (label_images.py): 150 fine-tune
the model and 150 test it (see splits.py and evaluate.py).

The thresholds were picked by looking at the feature spread across our 3,000
images, so that no single genre takes over the dataset.
"""

# The model's output order. cpp-core has a matching template for each name.
GENRES = ["EDM_CHILL", "EDM_DROP", "RETROWAVE", "CINEMATIC", "HOUSE"]

# Hue ranges on the 0-1 color wheel (multiply by 360 for degrees).
WARM_HUE_MAX = 0.20        # 0 to 72 degrees: red, orange, yellow
WARM_HUE_WRAP_MIN = 0.90   # 324 to 360 degrees: magenta wrapping back to red
GREEN_HUE = (0.20, 0.45)   # 72 to 162 degrees: yellow-green to green
BLUE_HUE = (0.45, 0.70)    # 162 to 252 degrees: cyan to blue


def estimate_energy(features) -> float:
    """Guess how energetic an image feels, from 0.3 (calm) to 0.9 (intense)."""
    _, _, _, _, _, saturation, colorfulness, contrast = features
    # Contrast only reaches 0.5, so double it to put it on the same 0-1 scale.
    raw = 0.5 * saturation + 0.3 * colorfulness + 0.2 * (contrast * 2.0)
    return 0.3 + 0.6 * min(max(raw, 0.0), 1.0)


def label_genre(features) -> str:
    """Pick a genre for one image's 8 features using hand-written rules."""
    _, _, _, brightness, hue, saturation, colorfulness, contrast = features
    energy = estimate_energy(features)

    # Dark images: intense ones drop, calm ones go cinematic.
    if brightness < 0.30:
        return "EDM_DROP" if energy > 0.55 else "CINEMATIC"

    # Bright images: intense ones are House, calm ones are chill.
    if brightness > 0.65:
        return "HOUSE" if energy > 0.60 else "EDM_CHILL"

    # Nearly black-and-white images: stylish retro or understated cinematic.
    if saturation < 0.15 and colorfulness < 0.25:
        return "RETROWAVE" if energy > 0.50 else "CINEMATIC"

    # Energetic warm colors feel like a drop.
    if energy > 0.58 and (hue < WARM_HUE_MAX or hue > WARM_HUE_WRAP_MIN):
        return "EDM_DROP"

    # Fairly bright with medium saturation looks like a retro poster.
    if brightness > 0.50 and 0.40 < saturation < 0.70:
        return "RETROWAVE"

    # Muted colors with strong contrast feel dramatic.
    if colorfulness < 0.35 and contrast > 0.22:
        return "CINEMATIC"

    # Blues and cyans feel cool and relaxed.
    if BLUE_HUE[0] < hue < BLUE_HUE[1]:
        return "EDM_CHILL"

    # Energetic greens feel uplifting.
    if GREEN_HUE[0] < hue < GREEN_HUE[1] and energy > 0.58:
        return "HOUSE"

    # Anything left is decided by energy, then brightness.
    if energy > 0.62:
        return "EDM_DROP"
    if energy > 0.55:
        return "HOUSE"
    if energy > 0.48:
        return "RETROWAVE"
    if brightness < 0.45:
        return "CINEMATIC"
    return "EDM_CHILL"
