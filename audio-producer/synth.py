import numpy as np
from scipy import signal

SAMPLE_RATE = 44100  # fluidsynth renders at this rate too (-r), so the arrays line up

# Fixed seed, so the same MIDI always gives the same WAV.
NOISE_SEED = 0


def time_axis(seconds: float) -> np.ndarray:
    return np.arange(int(seconds * SAMPLE_RATE)) / SAMPLE_RATE


def sine_sweep(frequencies_hz: np.ndarray) -> np.ndarray:
    # Phase is the running sum of the frequency; sin(2*pi*f(t)*t) is wrong once f changes.
    return np.sin(2 * np.pi * np.cumsum(frequencies_hz) / SAMPLE_RATE)


def filtered_noise(seconds: float, low_hz: float, high_hz: float | None = None) -> np.ndarray:
    noise = np.random.default_rng(NOISE_SEED).standard_normal(int(seconds * SAMPLE_RATE))
    if high_hz is None:
        sos = signal.butter(2, low_hz, "highpass", fs=SAMPLE_RATE, output="sos")
    else:
        sos = signal.butter(2, [low_hz, high_hz], "bandpass", fs=SAMPLE_RATE, output="sos")
    return signal.sosfilt(sos, noise)


def decay(seconds: float, time_constant: float) -> np.ndarray:
    return np.exp(-time_axis(seconds) / time_constant)


def place(track: np.ndarray, sound: np.ndarray, start_seconds: float, gain: float = 1.0) -> None:
    start = int(start_seconds * SAMPLE_RATE)
    end = min(start + len(sound), len(track))
    if start < end:
        track[start:end] += gain * sound[: end - start]
