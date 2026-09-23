"""Synthesizes the drum track from the drum notes in the song's MIDI.

Each genre has a kit: a handful of numbers that shape the same five recipes
(kick, snare, clap, hi-hat, crash). The MIDI note numbers are the General MIDI
percussion map, matching cpp-core's MusicTheory.hpp.
"""
from dataclasses import dataclass

import numpy as np

from synth import SAMPLE_RATE, decay, filtered_noise, place, sine_sweep, time_axis

# General MIDI percussion notes that cpp-core writes.
KICK, SNARE, CLAP, LOW_TOM, CLOSED_HAT, OPEN_HAT, CRASH = 36, 38, 39, 41, 42, 46, 49

# Sounds last five decay time-constants, by which point they have faded below 1%.
TAIL_LENGTH = 5


@dataclass
class Kit:
    kick_hz: float     # kick pitch; real kick drums sit around 40-70 Hz
    kick_decay: float  # seconds; short = punchy, long = boomy
    drive: float       # soft-clipping amount; higher = harder, more distorted kick
    snare_hz: float    # snare body pitch; real snares ring around 150-250 Hz
    hat_decay: float   # seconds; short = tight ticks, long = washy hats


# Chosen by ear to match each genre's usual sound.
KITS = {
    "HOUSE": Kit(kick_hz=60, kick_decay=0.18, drive=1.3, snare_hz=200, hat_decay=0.05),
    "EDM_CHILL": Kit(kick_hz=48, kick_decay=0.28, drive=1.1, snare_hz=180, hat_decay=0.08),
    "EDM_DROP": Kit(kick_hz=65, kick_decay=0.14, drive=1.8, snare_hz=220, hat_decay=0.04),
    "RETROWAVE": Kit(kick_hz=55, kick_decay=0.22, drive=1.4, snare_hz=190, hat_decay=0.06),
    "CINEMATIC": Kit(kick_hz=40, kick_decay=0.45, drive=0.9, snare_hz=160, hat_decay=0.10),
}


def pitched_drum(base_hz: float, decay_seconds: float, drive: float) -> np.ndarray:
    """A kick or tom: a sine that starts 5x higher and quickly falls to base_hz."""
    seconds = TAIL_LENGTH * decay_seconds
    pitch = base_hz * (1 + 4 * np.exp(-time_axis(seconds) * 40))
    body = sine_sweep(pitch) * decay(seconds, decay_seconds)
    return np.tanh(body * drive)


def snare(kit: Kit) -> np.ndarray:
    """A snare: a short tone for the drum head plus noise for the rattling wires."""
    seconds = 0.25
    head = np.sin(2 * np.pi * kit.snare_hz * time_axis(seconds)) * decay(seconds, 0.05)
    wires = filtered_noise(seconds, 1000, 8000) * decay(seconds, 0.07)
    return 0.5 * head + wires


def clap() -> np.ndarray:
    """A clap: three quick noise bursts, like several hands clapping slightly apart."""
    seconds = 0.3
    burst = np.zeros(int(seconds * SAMPLE_RATE))
    for offset in (0.0, 0.01, 0.02):
        place(burst, decay(seconds, 0.03), offset)
    return filtered_noise(seconds, 1000, 3000) * burst


def cymbal(decay_seconds: float, low_hz: float) -> np.ndarray:
    """A hi-hat or crash: bright noise with everything below low_hz removed."""
    seconds = TAIL_LENGTH * decay_seconds
    return filtered_noise(seconds, low_hz) * decay(seconds, decay_seconds)


def drum_sounds(genre: str) -> dict[int, np.ndarray]:
    """Every drum sound for a genre, keyed by its MIDI note."""
    kit = KITS[genre]
    sounds = {
        KICK: pitched_drum(kit.kick_hz, kit.kick_decay, kit.drive),
        SNARE: snare(kit),
        CLAP: clap(),
        LOW_TOM: pitched_drum(2 * kit.kick_hz, 0.4, 1.0),
        CLOSED_HAT: cymbal(kit.hat_decay, 7000),
        OPEN_HAT: cymbal(4 * kit.hat_decay, 7000),
        CRASH: cymbal(1.2, 5000),
    }
    return {note: sound / np.abs(sound).max() for note, sound in sounds.items()}


def render_drums(hits: list[tuple[float, int, int]], genre: str, length: int) -> np.ndarray:
    """Plays each (seconds, note, velocity) hit into a mono track `length` samples long."""
    sounds = drum_sounds(genre)
    track = np.zeros(length)
    for seconds, note, velocity in hits:
        place(track, sounds[note], seconds, gain=velocity / 127)
    return track
