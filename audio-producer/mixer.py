"""mix the 3 stems (instruments, drums, fx) -> master w/ ffmpeg"""
import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import soundfile as sf

from synth import SAMPLE_RATE, time_axis

# sidechain = every kick ducks the instruments for a sec and they swell back up.
# that "pumping" is a big part of why house/EDM sounds like house/EDM
DUCK_RECOVERY_SECONDS = 0.1  # time constant. ~fully back after 4x this (0.4s)


@dataclass
class Mix:
    instruments: float  # fluidsynth stem volume
    drums: float
    fx: float
    duck: float  # 0 = no ducking, 1 = instruments go silent on every kick


# dance genres pump hard, chill + cinematic barely duck
MIXES = {
    "HOUSE": Mix(instruments=0.8, drums=0.9, fx=0.5, duck=0.5),
    "EDM_DROP": Mix(instruments=0.8, drums=1.0, fx=0.6, duck=0.6),
    "EDM_CHILL": Mix(instruments=0.9, drums=0.7, fx=0.4, duck=0.3),
    "RETROWAVE": Mix(instruments=0.85, drums=0.8, fx=0.5, duck=0.3),
    "CINEMATIC": Mix(instruments=1.0, drums=0.7, fx=0.6, duck=0.1),
}

# mastering = 1 ffmpeg filter chain, runs in this order:
#   1. EQ   +3dB @100Hz (low end), -2dB @500Hz (mud), +2dB @8kHz (air)
#   2. comp 4:1 over -18dB, evens out loud vs quiet parts
#   3. loudnorm to -14 LUFS (what spotify/youtube normalize to anyway)
#   4. limiter so nothing clips
# order matters - loudnorm after comp or the comp undoes it
MASTERING_CHAIN = ",".join([
    "equalizer=f=100:t=h:width=200:g=3",
    "equalizer=f=500:t=h:width=400:g=-2",
    "equalizer=f=8000:t=h:width=2000:g=2",
    "acompressor=threshold=-18dB:ratio=4:attack=5:release=50:makeup=6dB",
    "loudnorm=I=-14:LRA=7:tp=-1",
    "alimiter=limit=0.95",
])
MASTER_TIMEOUT_SECONDS = 60  # normally a few sec, >60 = hung


def sidechain(kick_times: list[float], length: int, depth: float) -> np.ndarray:
    """gain curve, dips by depth on each kick. np.minimum so 2 close kicks don't stack weird"""
    curve = np.ones(length)
    dip = 1 - depth * np.exp(-time_axis(4 * DUCK_RECOVERY_SECONDS) / DUCK_RECOVERY_SECONDS)
    for seconds in kick_times:
        start = int(seconds * SAMPLE_RATE)
        end = min(start + len(dip), length)
        curve[start:end] = np.minimum(curve[start:end], dip[: end - start])
    return curve


def mix(instruments: np.ndarray, drums: np.ndarray, fx: np.ndarray,
        kick_times: list[float], genre: str) -> np.ndarray:
    """stereo instruments + mono drums/fx -> 1 stereo track. only the instruments get ducked.
    normalized to peak 1 here, loudness gets fixed in master()"""
    levels = MIXES[genre]
    ducking = sidechain(kick_times, len(instruments), levels.duck)
    mono_layers = levels.drums * drums + levels.fx * fx
    stereo = levels.instruments * instruments * ducking[:, None] + mono_layers[:, None]
    return stereo / np.abs(stereo).max()


def master(stereo: np.ndarray, work_dir: Path) -> bytes:
    """ffmpeg mastering -> 16-bit wav bytes. writes float wav first so nothing clips before the chain"""
    raw, done = work_dir / "mix.wav", work_dir / "master.wav"
    sf.write(raw, stereo, SAMPLE_RATE, subtype="FLOAT")
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw),
         "-af", MASTERING_CHAIN, "-ar", str(SAMPLE_RATE), "-c:a", "pcm_s16le", str(done)],
        check=True,
        timeout=MASTER_TIMEOUT_SECONDS,
    )
    return done.read_bytes()
