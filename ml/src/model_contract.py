"""
Phase 5.5 Model Contract
========================

This defines the exact input/output shape and meaning for the TF model.
Documented by Karan after training.
Daksh will eventually update C++ to match.

INPUT (8 floats):
-----------------
[0] avgR          : 0.0 - 1.0    (average red channel)
[1] avgG          : 0.0 - 1.0    (average green channel)
[2] avgB          : 0.0 - 1.0    (average blue channel)
[3] brightness    : 0.0 - 1.0    (luminance)
[4] hue           : 0.0 - 360.0  (HSV hue in degrees)
[5] saturation    : 0.0 - 1.0    (HSV saturation)
[6] colorfulness  : 0.0 - ~100.0 (colorfulness metric, normalized in practice)
[7] contrast      : 0.0 - 1.0    (edge contrast measure)

OUTPUT (7 floats):
------------------
[0] tempo_bpm      : 40.0 - 180.0  (ambient → EDM → drum&bass)
[1] base_frequency : 110.0 - 440.0 (Hz, A2-A4 range)
[2] energy         : 0.0 - 1.0     (note density / activity)
[3] brightness     : 0.0 - 1.0     (filter cutoff / timbre)
[4] reverb         : 0.0 - 1.0     (reverb amount)
[5] scale_type     : 0.0 - 3.0     (0=major, 1=minor, 2=dorian, 3=lydian)
[6] pattern_type   : 0.0 - 2.0     (0=pad, 1=arp, 2=chords)

Note: scale_type and pattern_type are discrete but encoded as floats.
C++ should round to nearest int when interpreting.

Model Architecture:
-------------------
- Input layer: 8 features
- Hidden layer 1: 128 units, ReLU, BatchNorm, Dropout(0.2)
- Hidden layer 2: 128 units, ReLU, BatchNorm, Dropout(0.2)
- Hidden layer 3: 64 units, ReLU
- Output layer: 7 parameters, Linear

Training Details:
-----------------
- Optimizer: Adam (lr=0.001)
- Loss: MSE
- Metrics: MAE
- Batch size: 32
- Max epochs: 100
- Early stopping: patience=15
- LR reduction: patience=5, factor=0.5
"""

INPUT_DIM = 8
OUTPUT_DIM = 7

# For validation and debugging
INPUT_NAMES = [
    "avgR",
    "avgG",
    "avgB",
    "brightness",
    "hue",
    "saturation",
    "colorfulness",
    "contrast"
]

OUTPUT_NAMES = [
    "tempo_bpm",
    "base_frequency",
    "energy",
    "brightness",
    "reverb",
    "scale_type",
    "pattern_type"
]

# Expected ranges for validation
INPUT_RANGES = {
    "avgR": (0.0, 1.0),
    "avgG": (0.0, 1.0),
    "avgB": (0.0, 1.0),
    "brightness": (0.0, 1.0),
    "hue": (0.0, 360.0),
    "saturation": (0.0, 1.0),
    "colorfulness": (0.0, 100.0),
    "contrast": (0.0, 1.0),
}

OUTPUT_RANGES = {
    "tempo_bpm": (40.0, 180.0),
    "base_frequency": (110.0, 440.0),
    "energy": (0.0, 1.0),
    "brightness": (0.0, 1.0),
    "reverb": (0.0, 1.0),
    "scale_type": (0.0, 3.0),
    "pattern_type": (0.0, 2.0),
}