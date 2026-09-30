"""The last step of a render: mixes the instruments, drums and effects at each genre's levels, then
masters the result with ffmpeg into the WAV the user hears."""
import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import soundfile as sf

from synth import SAMPLE_RATE, time_axis

DUCK_RECOVERY_SECONDS = 0.1  # time constant


@dataclass
class Mix:
    instruments: float
    drums: float
    fx: float
    duck: float  # 0 is none, 1 silences the instruments on each kick


MIXES = {
    "HOUSE": Mix(instruments=0.8, drums=0.9, fx=0.5, duck=0.5),
    "EDM_DROP": Mix(instruments=0.8, drums=1.0, fx=0.6, duck=0.6),
    "EDM_CHILL": Mix(instruments=0.9, drums=0.7, fx=0.4, duck=0.3),
    "RETROWAVE": Mix(instruments=0.85, drums=0.8, fx=0.5, duck=0.3),
    "CINEMATIC": Mix(instruments=1.0, drums=0.7, fx=0.6, duck=0.1),
}

# A little more bass, less mud in the mids, a bit of air on top, then compress, bring the
# loudness to -14 LUFS like streaming services do, and stop any peak going over.
# Order matters: loudnorm has to come after the compressor, or the compressor undoes it.
MASTERING_CHAIN = ",".join([
    "equalizer=f=100:t=h:width=200:g=3",
    "equalizer=f=500:t=h:width=400:g=-2",
    "equalizer=f=8000:t=h:width=2000:g=2",
    "acompressor=threshold=-18dB:ratio=4:attack=5:release=50:makeup=6dB",
    "loudnorm=I=-14:LRA=7:tp=-1",
    "alimiter=limit=0.95",
])
MASTER_TIMEOUT_SECONDS = 60


# Sidechain ducking: the instruments dip on every kick and come back over about 0.1 s. That
# pumping is a big part of the house and EDM sound.
def sidechain(kick_times: list[float], length: int, depth: float) -> np.ndarray:
    curve = np.ones(length)
    dip = 1 - depth * np.exp(-time_axis(4 * DUCK_RECOVERY_SECONDS) / DUCK_RECOVERY_SECONDS)
    for seconds in kick_times:
        start = int(seconds * SAMPLE_RATE)
        end = min(start + len(dip), length)
        # np.minimum, so two close kicks don't stack their dips.
        curve[start:end] = np.minimum(curve[start:end], dip[: end - start])
    return curve


# Scales the three layers, ducks the instruments on each kick, then peak-normalizes.
def mix(instruments: np.ndarray, drums: np.ndarray, fx: np.ndarray,
        kick_times: list[float], genre: str) -> np.ndarray:
    levels = MIXES[genre]
    ducking = sidechain(kick_times, len(instruments), levels.duck)
    # fluidsynth's output is stereo; drums and effects are mono, so they go equally in both sides.
    mono_layers = levels.drums * drums + levels.fx * fx
    stereo = levels.instruments * instruments * ducking[:, None] + mono_layers[:, None]
    return stereo / np.abs(stereo).max()


# Writes a float WAV, runs the ffmpeg chain, and returns 16-bit PCM bytes.
def master(stereo: np.ndarray, work_dir: Path) -> bytes:
    raw, done = work_dir / "mix.wav", work_dir / "master.wav"
    # Float WAV, so nothing clips before the mastering chain.
    sf.write(raw, stereo, SAMPLE_RATE, subtype="FLOAT")
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw),
         "-af", MASTERING_CHAIN, "-ar", str(SAMPLE_RATE), "-c:a", "pcm_s16le", str(done)],
        check=True,
        timeout=MASTER_TIMEOUT_SECONDS,
    )
    return done.read_bytes()
