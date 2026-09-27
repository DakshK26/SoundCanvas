"""Small building blocks for synthesizing sounds with numpy."""
import numpy as np
from scipy import signal

SAMPLE_RATE = 44100  # CD-quality samples per second; FluidSynth renders at the same rate

# Noise comes from a fixed seed, like a recorded drum sample: the same MIDI always
# renders the same WAV, and concurrent renders share no random state.
NOISE_SEED = 0


def time_axis(seconds: float) -> np.ndarray:
    """The time in seconds of every sample in a sound of the given length."""
    return np.arange(int(seconds * SAMPLE_RATE)) / SAMPLE_RATE


def sine_sweep(frequencies_hz: np.ndarray) -> np.ndarray:
    """A sine wave whose pitch follows the given per-sample frequencies."""
    return np.sin(2 * np.pi * np.cumsum(frequencies_hz) / SAMPLE_RATE)


def filtered_noise(seconds: float, low_hz: float, high_hz: float | None = None) -> np.ndarray:
    """White noise kept above low_hz, and below high_hz if given."""
    noise = np.random.default_rng(NOISE_SEED).standard_normal(int(seconds * SAMPLE_RATE))
    if high_hz is None:
        sos = signal.butter(2, low_hz, "highpass", fs=SAMPLE_RATE, output="sos")
    else:
        sos = signal.butter(2, [low_hz, high_hz], "bandpass", fs=SAMPLE_RATE, output="sos")
    return signal.sosfilt(sos, noise)


def decay(seconds: float, time_constant: float) -> np.ndarray:
    """An exponential fade from 1 toward 0. It drops to 37% every time_constant seconds."""
    return np.exp(-time_axis(seconds) / time_constant)


def place(track: np.ndarray, sound: np.ndarray, start_seconds: float, gain: float = 1.0) -> None:
    """Adds a sound into a longer track at the given time, cutting it off at the track's end."""
    start = int(start_seconds * SAMPLE_RATE)
    end = min(start + len(sound), len(track))
    if start < end:
        track[start:end] += gain * sound[: end - start]
