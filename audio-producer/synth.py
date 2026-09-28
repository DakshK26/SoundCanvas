"""numpy synth helpers used by drums.py and fx.py"""
import numpy as np
from scipy import signal

SAMPLE_RATE = 44100  # CD rate. fluidsynth gets told to use the same (-r) so the arrays line up

# fixed seed -> noise is the same every time, basically like using a recorded sample.
# same midi = same wav, and a fresh rng per call means parallel renders don't share state
NOISE_SEED = 0


def time_axis(seconds: float) -> np.ndarray:
    """t for every sample, in seconds"""
    return np.arange(int(seconds * SAMPLE_RATE)) / SAMPLE_RATE


def sine_sweep(frequencies_hz: np.ndarray) -> np.ndarray:
    """sine w/ changing pitch. learned: have to integrate freq (cumsum) to get phase,
    sin(2pi * f(t) * t) sounds wrong when f changes"""
    return np.sin(2 * np.pi * np.cumsum(frequencies_hz) / SAMPLE_RATE)


def filtered_noise(seconds: float, low_hz: float, high_hz: float | None = None) -> np.ndarray:
    """white noise -> highpass at low_hz, or bandpass if high_hz given. 2nd order butterworth"""
    noise = np.random.default_rng(NOISE_SEED).standard_normal(int(seconds * SAMPLE_RATE))
    if high_hz is None:
        sos = signal.butter(2, low_hz, "highpass", fs=SAMPLE_RATE, output="sos")
    else:
        sos = signal.butter(2, [low_hz, high_hz], "bandpass", fs=SAMPLE_RATE, output="sos")
    return signal.sosfilt(sos, noise)


def decay(seconds: float, time_constant: float) -> np.ndarray:
    """exp fade 1 -> 0, down to 37% (1/e) after each time_constant"""
    return np.exp(-time_axis(seconds) / time_constant)


def place(track: np.ndarray, sound: np.ndarray, start_seconds: float, gain: float = 1.0) -> None:
    """mix sound into track at start_seconds (in place). anything past the end gets cut"""
    start = int(start_seconds * SAMPLE_RATE)
    end = min(start + len(sound), len(track))
    if start < end:
        track[start:end] += gain * sound[: end - start]
