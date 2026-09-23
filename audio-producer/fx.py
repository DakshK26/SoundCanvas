"""Transition effects placed at the section markers cpp-core writes into the MIDI.

- A rising sweep (uplifter) builds into every drop.
- A boom (impact) lands on the first beat of every drop.
- A falling sweep (downlifter) opens every break as the energy winds down.
"""
import numpy as np

from synth import decay, filtered_noise, place, sine_sweep, time_axis

SWEEP_SECONDS = 2.0   # about one bar at dance tempos
IMPACT_SECONDS = 1.5


def uplifter() -> np.ndarray:
    """A tone and hiss that rise from 200 Hz to 2 kHz while getting louder."""
    progress = time_axis(SWEEP_SECONDS) / SWEEP_SECONDS
    tone = sine_sweep(200 * 10**progress)
    hiss = filtered_noise(SWEEP_SECONDS, 2000)
    return progress**2 * (0.5 * tone + 0.2 * hiss)


def impact() -> np.ndarray:
    """A deep boom: a sine falling from 150 Hz to 40 Hz as it fades."""
    progress = time_axis(IMPACT_SECONDS) / IMPACT_SECONDS
    return sine_sweep(150 * (40 / 150) ** progress) * decay(IMPACT_SECONDS, 0.3)


def render_fx(markers: list[tuple[float, str]], length: int) -> np.ndarray:
    """Places effects around each (seconds, section name) marker in a mono track."""
    track = np.zeros(length)
    for seconds, section in markers:
        if section == "drop":
            place(track, uplifter(), max(0.0, seconds - SWEEP_SECONDS))
            place(track, impact(), seconds)
        elif section == "break":
            place(track, uplifter()[::-1], seconds)
    return track
