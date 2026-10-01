"""Small building blocks for making sounds in numpy: sweeps, filtered noise, fades, and place() to
drop a sound into a track. drums.py and fx.py build their sounds from these, mixer.py uses
time_axis for the ducking curve, and app.py passes SAMPLE_RATE to fluidsynth."""
import numpy as np
from scipy import signal

SAMPLE_RATE = 44100  # fluidsynth renders at this rate too (-r), so the arrays line up

# Fixed seed, so the same MIDI always gives the same WAV.
NOISE_SEED = 0


# Sample times in seconds, from 0 up to just under `seconds`. Sample n is at n / SAMPLE_RATE.
def time_axis(seconds: float) -> np.ndarray:
    return np.arange(int(seconds * SAMPLE_RATE)) / SAMPLE_RATE


# A sine whose pitch follows frequencies_hz, one frequency per sample.
def sine_sweep(frequencies_hz: np.ndarray) -> np.ndarray:
    # Phase is the running sum of the frequency; sin(2*pi*f(t)*t) is wrong once f changes.
    # Each sample moves the wave forward by f / SAMPLE_RATE cycles, so cumsum gives the cycles
    # done so far, and 2*pi turns cycles into radians.
    return np.sin(2 * np.pi * np.cumsum(frequencies_hz) / SAMPLE_RATE)


# White noise with the lows cut, and the highs too if high_hz is given. Hats, snares and risers
# all start from this.
def filtered_noise(seconds: float, low_hz: float, high_hz: float | None = None) -> np.ndarray:
    # A new generator with the same seed each call, so the noise is identical on every render.
    noise = np.random.default_rng(NOISE_SEED).standard_normal(int(seconds * SAMPLE_RATE))
    # A 2nd-order Butterworth filter. "sos" (second-order sections) is the numerically safe form
    # scipy recommends for applying it.
    if high_hz is None:
        sos = signal.butter(2, low_hz, "highpass", fs=SAMPLE_RATE, output="sos")
    else:
        sos = signal.butter(2, [low_hz, high_hz], "bandpass", fs=SAMPLE_RATE, output="sos")
    return signal.sosfilt(sos, noise)


# Exponential fade, e^(-t / time_constant): 1 at the start, shrinking by the same factor every
# time_constant seconds. After about 5 time constants the sound is under 1%.
def decay(seconds: float, time_constant: float) -> np.ndarray:
    return np.exp(-time_axis(seconds) / time_constant)


# Adds a sound into the track at a time, cut off at the end of the track.
def place(track: np.ndarray, sound: np.ndarray, start_seconds: float, gain: float = 1.0) -> None:
    start = int(start_seconds * SAMPLE_RATE)
    end = min(start + len(sound), len(track))
    # Skips a sound that starts after the track ends. += mixes it with whatever is already
    # there, so overlapping hits add up instead of replacing each other.
    if start < end:
        track[start:end] += gain * sound[: end - start]
