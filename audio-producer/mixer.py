"""Mixes the instrument, drum and FX tracks, then masters the result with ffmpeg."""
import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import soundfile as sf

from synth import SAMPLE_RATE, time_axis

# Sidechain: each kick briefly ducks the instruments, then they swell back.
# This "pumping" is the signature sound of house and EDM.
DUCK_RECOVERY_SECONDS = 0.1  # 37% recovered after this long; fully back after ~0.4 s


@dataclass
class Mix:
    instruments: float  # volume of the FluidSynth-rendered instruments
    drums: float
    fx: float
    duck: float  # how far a kick ducks the instruments: 0 = not at all, 1 = to silence


# Dance genres pump hard; chill and cinematic keep the instruments steady.
MIXES = {
    "HOUSE": Mix(instruments=0.8, drums=0.9, fx=0.5, duck=0.5),
    "EDM_DROP": Mix(instruments=0.8, drums=1.0, fx=0.6, duck=0.6),
    "EDM_CHILL": Mix(instruments=0.9, drums=0.7, fx=0.4, duck=0.3),
    "RETROWAVE": Mix(instruments=0.85, drums=0.8, fx=0.5, duck=0.3),
    "CINEMATIC": Mix(instruments=1.0, drums=0.7, fx=0.6, duck=0.1),
}

# One ffmpeg filter chain, applied in order:
#   1. EQ: +3 dB of low end at 100 Hz, -2 dB of "mud" at 500 Hz, +2 dB of sparkle at 8 kHz.
#   2. Compressor: evens out loud and quiet moments (4:1 above -18 dB).
#   3. Loudness: -14 LUFS, the level Spotify and YouTube normalize songs to.
#   4. Limiter: stops any peak from clipping.
MASTERING_CHAIN = ",".join([
    "equalizer=f=100:t=h:width=200:g=3",
    "equalizer=f=500:t=h:width=400:g=-2",
    "equalizer=f=8000:t=h:width=2000:g=2",
    "acompressor=threshold=-18dB:ratio=4:attack=5:release=50:makeup=6dB",
    "loudnorm=I=-14:LRA=7:tp=-1",
    "alimiter=limit=0.95",
])
MASTER_TIMEOUT_SECONDS = 60  # mastering takes a few seconds; one still running after a minute is hung


def sidechain(kick_times: list[float], length: int, depth: float) -> np.ndarray:
    """A volume curve that dips by `depth` at every kick and recovers after it."""
    curve = np.ones(length)
    dip = 1 - depth * np.exp(-time_axis(4 * DUCK_RECOVERY_SECONDS) / DUCK_RECOVERY_SECONDS)
    for seconds in kick_times:
        start = int(seconds * SAMPLE_RATE)
        end = min(start + len(dip), length)
        curve[start:end] = np.minimum(curve[start:end], dip[: end - start])
    return curve


def mix(instruments: np.ndarray, drums: np.ndarray, fx: np.ndarray,
        kick_times: list[float], genre: str) -> np.ndarray:
    """Combines stereo instruments with mono drums and FX into one stereo track."""
    levels = MIXES[genre]
    ducking = sidechain(kick_times, len(instruments), levels.duck)
    mono_layers = levels.drums * drums + levels.fx * fx
    stereo = levels.instruments * instruments * ducking[:, None] + mono_layers[:, None]
    return stereo / np.abs(stereo).max()


def master(stereo: np.ndarray, work_dir: Path) -> bytes:
    """Runs the mastering chain and returns the finished 16-bit WAV file."""
    raw, done = work_dir / "mix.wav", work_dir / "master.wav"
    sf.write(raw, stereo, SAMPLE_RATE, subtype="FLOAT")
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw),
         "-af", MASTERING_CHAIN, "-ar", str(SAMPLE_RATE), "-c:a", "pcm_s16le", str(done)],
        check=True,
        timeout=MASTER_TIMEOUT_SECONDS,
    )
    return done.read_bytes()
