"""Risers and impacts placed on the section markers cpp-core writes into the MIDI."""
import numpy as np

from synth import decay, filtered_noise, place, sine_sweep, time_axis

SWEEP_SECONDS = 2.0
IMPACT_SECONDS = 1.5


# A tone rising from 200 Hz to 2 kHz, plus hiss, getting louder over 2 seconds.
def uplifter() -> np.ndarray:
    progress = time_axis(SWEEP_SECONDS) / SWEEP_SECONDS
    tone = sine_sweep(200 * 10**progress)
    hiss = filtered_noise(SWEEP_SECONDS, 2000)
    return progress**2 * (0.5 * tone + 0.2 * hiss)


# A deep boom falling from 150 Hz to 40 Hz.
def impact() -> np.ndarray:
    progress = time_axis(IMPACT_SECONDS) / IMPACT_SECONDS
    return sine_sweep(150 * (40 / 150) ** progress) * decay(IMPACT_SECONDS, 0.3)


def render_fx(markers: list[tuple[float, str]], length: int) -> np.ndarray:
    track = np.zeros(length)
    # A riser that ends right on each drop and a boom on its first beat. A break gets the riser
    # backwards, so the energy falls away.
    for seconds, section in markers:
        if section == "drop":
            place(track, uplifter(), max(0.0, seconds - SWEEP_SECONDS))
            place(track, impact(), seconds)
        elif section == "break":
            place(track, uplifter()[::-1], seconds)
    return track
