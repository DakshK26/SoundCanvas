"""Risers and impacts placed on the section markers cpp-core writes into the MIDI (Composer.cpp,
with the names from GenreTemplate.cpp). app.py passes in the markers it read and gets back one
mono track. The sounds are built from the helpers in synth.py."""
import numpy as np

from synth import decay, filtered_noise, place, sine_sweep, time_axis

SWEEP_SECONDS = 2.0
IMPACT_SECONDS = 1.5


# A tone rising from 200 Hz to 2 kHz, plus hiss, getting louder over 2 seconds.
def uplifter() -> np.ndarray:
    # progress goes from 0 to 1 over the sweep.
    progress = time_axis(SWEEP_SECONDS) / SWEEP_SECONDS
    # 10**progress goes from 1 to 10, so the pitch climbs from 200 to 2000 Hz. Being exponential,
    # it rises by the same musical interval each moment instead of bunching up at the top.
    tone = sine_sweep(200 * 10**progress)
    hiss = filtered_noise(SWEEP_SECONDS, 2000)
    # progress**2 is the volume: quiet for most of the sweep, then swelling fast near the end.
    return progress**2 * (0.5 * tone + 0.2 * hiss)


# A deep boom falling from 150 Hz to 40 Hz.
def impact() -> np.ndarray:
    progress = time_axis(IMPACT_SECONDS) / IMPACT_SECONDS
    # (40 / 150) ** progress goes from 1 down to 40/150, so the pitch slides 150 to 40 Hz,
    # while the fade (0.3 s time constant) makes it a short hit.
    return sine_sweep(150 * (40 / 150) ** progress) * decay(IMPACT_SECONDS, 0.3)


def render_fx(markers: list[tuple[float, str]], length: int) -> np.ndarray:
    track = np.zeros(length)
    # A riser that ends right on each drop and a boom on its first beat. A break gets the riser
    # backwards, so the energy falls away. Other markers ("intro", "build", "outro") get nothing.
    for seconds, section in markers:
        if section == "drop":
            # max() stops a drop in the first 2 seconds from giving a negative start time.
            place(track, uplifter(), max(0.0, seconds - SWEEP_SECONDS))
            place(track, impact(), seconds)
        elif section == "break":
            # [::-1] reverses the array, so it starts loud and high and fades down.
            place(track, uplifter()[::-1], seconds)
    return track
