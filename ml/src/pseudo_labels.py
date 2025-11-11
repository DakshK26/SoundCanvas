# ml/src/pseudo_labels.py
from __future__ import annotations
import numpy as np
from dataclasses import dataclass

@dataclass
class MusicParameters:
    """
    7-dimensional music control vector for ambient sound synthesis.
    
    All parameters are designed to stay within musically pleasant ranges.
    """
    tempo_bpm: float         # 40-180 BPM (ambient → EDM → drum&bass)
    base_frequency: float    # 100-400 Hz (bass to mid range)
    energy: float            # 0.0-1.0 (how busy/dense the texture)
    brightness: float        # 0.0-1.0 (filter cutoff, waveform choice)
    reverb: float            # 0.0-1.0 (dry to big hall)
    scale_type: int          # 0=major, 1=minor, 2=dorian, 3=lydian
    pattern_type: int        # 0=pad, 1=arp, 2=chords

def clamp01(x: float) -> float:
    """Clamp value to [0, 1] range."""
    return max(0.0, min(1.0, x))

def clamp(x: float, lo: float, hi: float) -> float:
    """Clamp value to [lo, hi] range."""
    return max(lo, min(hi, x))

def map_features_to_music(features: np.ndarray) -> MusicParameters:
    """
    Map 8-dim image features to 7-dim music parameters using hand-designed rules.
    
    Input features (8-dim):
        [avgR, avgG, avgB, brightness, hue, saturation, colorfulness, contrast]
    
    Output parameters (7-dim):
        [tempo_bpm, base_frequency, energy, brightness, reverb, scale_type, pattern_type]
    
    Mapping philosophy:
        - brightness → tempo + reverb (dark=slow+reverb, bright=faster+dry)
        - hue → scale_type (blue=minor, green=lydian, red=mixolydian/major)
        - saturation/colorfulness → energy + pattern_type (vivid=busier, muted=simple)
        - contrast → dynamics and texture variation
        - avgB (blue channel) → base_frequency (cooler=lower, warmer=higher)
    """
    avg_r, avg_g, avg_b, brightness, hue, saturation, colorfulness, contrast = features.tolist()
    
    # Ensure all inputs are in valid ranges
    brightness = clamp01(brightness)
    hue = clamp01(hue)
    saturation = clamp01(saturation)
    colorfulness = clamp01(colorfulness)
    contrast = clamp01(contrast)
    
    # === TEMPO: darker images → slower, brighter → faster ===
    # Range: 40-180 BPM (ambient → house → EDM → drum&bass)
    tempo_bpm = 40.0 + brightness * 100.0  # Dark: ~40, Bright: ~140
    
    # Add variation from saturation and contrast (colorful/high contrast → faster)
    tempo_bpm += saturation * 30.0  # Colorful = energetic
    tempo_bpm += contrast * 15.0    # High contrast → faster
    tempo_bpm = clamp(tempo_bpm, 40.0, 180.0)
    
    # === BASE FREQUENCY: influenced by color temperature ===
    # Blue-ish (cool) → lower frequencies
    # Red-ish (warm) → higher frequencies
    # Range: 100-400 Hz
    
    # Compute "warmth" from R vs B balance
    warmth = (avg_r - avg_b + 1.0) / 2.0  # Maps to [0, 1] approx
    warmth = clamp01(warmth)
    
    base_frequency = 100.0 + warmth * 300.0  # Cool: ~100Hz, Warm: ~400Hz
    
    # === ENERGY: saturation + colorfulness → busier textures ===
    # Range: 0.0-1.0
    # Low saturation → simple drones
    # High saturation → richer, more active textures
    energy = (saturation * 0.6 + colorfulness * 0.4)
    energy = clamp01(energy)
    
    # === BRIGHTNESS (timbre): matches visual brightness ===
    # Range: 0.0-1.0
    # Controls filter cutoff / waveform selection
    timbre_brightness = brightness
    
    # === REVERB: darker/moodier images → more reverb (distant feel) ===
    # Range: 0.0-1.0
    # Dark images → spacious, ethereal
    # Bright images → more present, less reverb
    reverb = 1.0 - brightness  # Inverted: dark=1.0, bright=0.0
    
    # Add influence from saturation (desaturated → more reverb/distance)
    reverb = reverb * 0.7 + (1.0 - saturation) * 0.3
    reverb = clamp01(reverb)
    
    # === SCALE TYPE: hue → harmonic flavor ===
    # 0 = major (warm, uplifting)
    # 1 = minor (cool, introspective)
    # 2 = dorian (balanced, jazzy)
    # 3 = lydian (bright, dreamy)
    
    # Hue ranges (approximate):
    # Red/Orange: 0.0-0.15 → major/mixolydian
    # Yellow/Green: 0.15-0.45 → lydian
    # Cyan/Blue: 0.45-0.65 → minor
    # Purple/Magenta: 0.65-1.0 → dorian
    
    if hue < 0.15:
        scale_type = 0  # major (warm reds/oranges)
    elif hue < 0.45:
        scale_type = 3  # lydian (yellow/green, bright and open)
    elif hue < 0.65:
        scale_type = 1  # minor (blue, cool and introspective)
    else:
        scale_type = 2  # dorian (purple/magenta, balanced)
    
    # === PATTERN TYPE: energy level determines texture complexity ===
    # 0 = pad (sustained drone, simple)
    # 1 = arp (gentle arpeggios, medium)
    # 2 = chords (block chords, more harmonic movement)
    
    if energy < 0.35:
        pattern_type = 0  # Low energy → simple pad
    elif energy < 0.70:
        pattern_type = 1  # Medium energy → gentle arpeggios
    else:
        pattern_type = 2  # High energy → chord progression
    
    return MusicParameters(
        tempo_bpm=tempo_bpm,
        base_frequency=base_frequency,
        energy=energy,
        brightness=timbre_brightness,
        reverb=reverb,
        scale_type=scale_type,
        pattern_type=pattern_type,
    )

def music_params_to_vector(mp: MusicParameters) -> np.ndarray:
    """
    Convert MusicParameters to fixed 7-dim numpy vector.
    
    Order (must be consistent for training & inference):
        [tempo_bpm, base_frequency, energy, brightness, reverb, scale_type, pattern_type]
    
    Note: scale_type and pattern_type are integers, but stored as float32 for training.
    C++ will round them when interpreting.
    """
    return np.array(
        [
            mp.tempo_bpm,
            mp.base_frequency,
            mp.energy,
            mp.brightness,
            mp.reverb,
            float(mp.scale_type),   # Cast int to float for model
            float(mp.pattern_type),  # Cast int to float for model
        ],
        dtype=np.float32,
    )
