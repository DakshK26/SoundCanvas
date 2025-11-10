# ml/src/pseudo_labels.py
from __future__ import annotations
import numpy as np
from dataclasses import dataclass

@dataclass
class MusicParameters:
    tempo_bpm: float
    base_frequency: float
    brightness: float
    volume: float
    duration_seconds: float

def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))

def map_features_to_music(features: np.ndarray) -> MusicParameters:
    avg_r, avg_g, avg_b, brightness = features.tolist()
    brightness = clamp01(brightness)

    tempo = 40.0 + brightness * 60.0        # 40–100 BPM
    base_freq = 110.0 + avg_b * 220.0      # 110–330 Hz
    volume = 0.5
    duration = 8.0 + (1.0 - brightness) * 4.0  # 8–12 seconds

    return MusicParameters(
        tempo_bpm=tempo,
        base_frequency=base_freq,
        brightness=brightness,
        volume=volume,
        duration_seconds=duration,
    )

def music_params_to_vector(mp: MusicParameters) -> np.ndarray:
    # Order must be consistent for training & inference
    return np.array(
        [
            mp.tempo_bpm,
            mp.base_frequency,
            mp.brightness,
            mp.volume,
            mp.duration_seconds,
        ],
        dtype=np.float32,
    )
