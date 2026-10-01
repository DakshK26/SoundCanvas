"""Drums synthesized from the MIDI drum notes, with one Kit of settings per genre. render.py passes
in the drum hits midi.py read from the MIDI and gets back one mono track. The sounds are built from the
helpers in synth.py, and KITS also doubles as app.py's list of valid genres."""
from dataclasses import dataclass

import numpy as np

from synth import SAMPLE_RATE, decay, filtered_noise, place, sine_sweep, time_axis

# GM percussion notes, must match cpp-core/include/MusicTheory.hpp. A note cpp-core writes that
# is missing here would fail the lookup in render_drums.
KICK, SNARE, CLAP, LOW_TOM, CLOSED_HAT, OPEN_HAT, CRASH = 36, 38, 39, 41, 42, 46, 49

# Time constants before a sound is cut; e^-5 is under 1%.
TAIL_LENGTH = 5


# The settings that make one genre's kit sound different from another's.
@dataclass
class Kit:
    kick_hz: float     # the pitch the kick settles on
    kick_decay: float  # seconds
    drive: float       # how hard tanh saturates the kick
    snare_hz: float    # pitch of the snare's drum head tone
    hat_decay: float   # seconds


# Tuned by ear. The keys are the genre names the worker sends in ?genre=.
KITS = {
    "HOUSE": Kit(kick_hz=60, kick_decay=0.18, drive=1.3, snare_hz=200, hat_decay=0.05),
    "EDM_CHILL": Kit(kick_hz=48, kick_decay=0.28, drive=1.1, snare_hz=180, hat_decay=0.08),
    "EDM_DROP": Kit(kick_hz=65, kick_decay=0.14, drive=1.8, snare_hz=220, hat_decay=0.04),
    "CINEMATIC": Kit(kick_hz=40, kick_decay=0.45, drive=0.9, snare_hz=160, hat_decay=0.10),
}


# A kick is a sine that starts at 5 times its pitch, drops fast, then fades. tanh saturates it
# for punch; more drive is a harder kick.
def pitched_drum(base_hz: float, decay_seconds: float, drive: float) -> np.ndarray:
    seconds = TAIL_LENGTH * decay_seconds
    # 1 + 4 * e^(-40t) starts at 5 and falls towards 1 with a time constant of 1/40 s, so the
    # pitch slides from 5 * base_hz down to base_hz. That quick slide is the "thump".
    pitch = base_hz * (1 + 4 * np.exp(-time_axis(seconds) * 40))
    body = sine_sweep(pitch) * decay(seconds, decay_seconds)
    # tanh is nearly straight for small values and flattens towards 1 and -1 for big ones.
    # Multiplying by drive first pushes more of the wave into the flat part, rounding off the
    # peaks (soft clipping), which makes the kick sound fuller and harder.
    return np.tanh(body * drive)


# A short tone for the drum head plus band-passed noise for the wires under it.
def snare(kit: Kit) -> np.ndarray:
    seconds = 0.25
    head = np.sin(2 * np.pi * kit.snare_hz * time_axis(seconds)) * decay(seconds, 0.05)
    wires = filtered_noise(seconds, 1000, 8000) * decay(seconds, 0.07)
    # The tone at half level, so the noisy wires are what you mostly hear.
    return 0.5 * head + wires


# Three bursts of noise 10 ms apart, like a few hands clapping not quite together.
def clap() -> np.ndarray:
    seconds = 0.3
    # burst is a volume shape, not a sound: three fades added on top of each other, one starting
    # at 0, 10 and 20 ms. Multiplying the noise by it gives the three bursts.
    burst = np.zeros(int(seconds * SAMPLE_RATE))
    for offset in (0.0, 0.01, 0.02):
        place(burst, decay(seconds, 0.03), offset)
    return filtered_noise(seconds, 1000, 3000) * burst


# Hats and crashes are high-passed noise; mostly the fade time tells them apart.
def cymbal(decay_seconds: float, low_hz: float) -> np.ndarray:
    seconds = TAIL_LENGTH * decay_seconds
    return filtered_noise(seconds, low_hz) * decay(seconds, decay_seconds)


# Builds each kit sound once, then render_drums stamps them onto the track.
def drum_sounds(genre: str) -> dict[int, np.ndarray]:
    kit = KITS[genre]
    sounds = {
        KICK: pitched_drum(kit.kick_hz, kit.kick_decay, kit.drive),
        SNARE: snare(kit),
        CLAP: clap(),
        # The tom is the kick recipe an octave higher, with a longer fade and light drive.
        LOW_TOM: pitched_drum(2 * kit.kick_hz, 0.4, 1.0),
        CLOSED_HAT: cymbal(kit.hat_decay, 7000),
        # An open hat rings 4 times longer than the closed one.
        OPEN_HAT: cymbal(4 * kit.hat_decay, 7000),
        CRASH: cymbal(1.2, 5000),
    }
    # Every sound peaks at 1, so the MIDI velocity alone sets how loud a hit is.
    return {note: sound / np.abs(sound).max() for note, sound in sounds.items()}


# Places every MIDI drum hit onto a silent track of the same length as the instruments.
def render_drums(hits: list[tuple[float, int, int]], genre: str, length: int) -> np.ndarray:
    sounds = drum_sounds(genre)
    track = np.zeros(length)
    # MIDI velocity runs up to 127, so velocity / 127 is a volume between 0 and 1.
    for seconds, note, velocity in hits:
        place(track, sounds[note], seconds, gain=velocity / 127)
    return track
