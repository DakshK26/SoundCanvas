"""transition fx, placed using the section markers cpp-core puts in the midi

- uplifter (rising sweep) going into every drop
- impact (boom) on beat 1 of every drop
- downlifter (falling sweep) at the start of every break
"""
import numpy as np

from synth import decay, filtered_noise, place, sine_sweep, time_axis

SWEEP_SECONDS = 2.0   # ~1 bar at dance tempos
IMPACT_SECONDS = 1.5


def uplifter() -> np.ndarray:
    """tone + hiss rising 200Hz -> 2kHz and getting louder"""
    progress = time_axis(SWEEP_SECONDS) / SWEEP_SECONDS
    tone = sine_sweep(200 * 10**progress)
    hiss = filtered_noise(SWEEP_SECONDS, 2000)
    return progress**2 * (0.5 * tone + 0.2 * hiss)


def impact() -> np.ndarray:
    """deep boom, sine falling 150 -> 40Hz while it fades"""
    progress = time_axis(IMPACT_SECONDS) / IMPACT_SECONDS
    return sine_sweep(150 * (40 / 150) ** progress) * decay(IMPACT_SECONDS, 0.3)


def render_fx(markers: list[tuple[float, str]], length: int) -> np.ndarray:
    """mono fx track. uplifter ends right on the drop, downlifter = uplifter reversed"""
    track = np.zeros(length)
    for seconds, section in markers:
        if section == "drop":
            place(track, uplifter(), max(0.0, seconds - SWEEP_SECONDS))
            place(track, impact(), seconds)
        elif section == "break":
            place(track, uplifter()[::-1], seconds)
    return track
