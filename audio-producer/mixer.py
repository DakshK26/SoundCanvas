"""The last step of a render: mixes the instruments, drums and effects at each genre's levels, then
masters the result with ffmpeg into the WAV the user hears. render.py's render_song calls mix() and
then master(); the drums and effects come from drums.py and fx.py."""
import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import soundfile as sf

from synth import SAMPLE_RATE, time_axis

DUCK_RECOVERY_SECONDS = 0.1  # time constant


# How loud each layer is in one genre, and how hard the kick ducks the instruments.
@dataclass
class Mix:
    instruments: float
    drums: float
    fx: float
    duck: float  # 0 is none, 1 silences the instruments on each kick


# Same genre keys as KITS in drums.py. HOUSE and EDM_DROP duck hardest for the pumping sound;
# CINEMATIC barely ducks.
MIXES = {
    "HOUSE": Mix(instruments=0.8, drums=0.9, fx=0.5, duck=0.5),
    "EDM_DROP": Mix(instruments=0.8, drums=1.0, fx=0.6, duck=0.6),
    "EDM_CHILL": Mix(instruments=0.9, drums=0.7, fx=0.4, duck=0.3),
    "CINEMATIC": Mix(instruments=1.0, drums=0.7, fx=0.6, duck=0.1),
}

# A little more bass, less mud in the mids, a bit of air on top, then compress, bring the
# loudness to -14 LUFS like streaming services do, and stop any peak going over.
# Order matters: loudnorm has to come after the compressor, or the compressor undoes it.
# ffmpeg runs the filters left to right, joined by commas:
#   equalizer f=100, width 200 Hz (t=h means width in Hz), g=3: boost 3 dB around 100 Hz (bass).
#   equalizer f=500, width 400 Hz, g=-2: cut 2 dB around 500 Hz, where a mix gets muddy.
#   equalizer f=8000, width 2000 Hz, g=2: boost 2 dB around 8 kHz (air).
#   acompressor: above -18 dB, every 4 dB louder in comes out only 1 dB louder (ratio 4). It reacts
#     in 5 ms (attack), lets go over 50 ms (release), then adds 6 dB back (makeup).
#   loudnorm: I=-14 is the target loudness in LUFS, LRA=7 the allowed loudness range, and tp=-1
#     keeps true peaks at or under -1 dBTP.
#   alimiter: a hard ceiling at 0.95 of full scale, so no sample clips.
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
    # One volume value per sample. 1 means the instruments play at full level.
    curve = np.ones(length)
    # The shape of one dip, 4 time constants long. At the kick it is 1 - depth, then the
    # e^(-t / 0.1) part fades out and the volume climbs back towards 1.
    dip = 1 - depth * np.exp(-time_axis(4 * DUCK_RECOVERY_SECONDS) / DUCK_RECOVERY_SECONDS)
    for seconds in kick_times:
        start = int(seconds * SAMPLE_RATE)
        # Cut the dip short if the kick is near the end of the song.
        end = min(start + len(dip), length)
        # np.minimum, so two close kicks don't stack their dips.
        # It keeps the lower of the two values at each sample, so the curve never goes below
        # 1 - depth. Multiplying the dips together would push it lower on fast kick patterns.
        curve[start:end] = np.minimum(curve[start:end], dip[: end - start])
    return curve


# Scales the three layers, ducks the instruments on each kick, then peak-normalizes.
def mix(instruments: np.ndarray, drums: np.ndarray, fx: np.ndarray,
        kick_times: list[float], genre: str) -> np.ndarray:
    levels = MIXES[genre]
    ducking = sidechain(kick_times, len(instruments), levels.duck)
    # fluidsynth's output is stereo; drums and effects are mono, so they go equally in both sides.
    mono_layers = levels.drums * drums + levels.fx * fx
    # instruments has shape (samples, 2) but ducking has one value per sample, shape (samples,).
    # [:, None] turns it into a column of shape (samples, 1), so numpy scales the left and right
    # channel of each sample by the same amount. mono_layers[:, None] does the same for the mono
    # drums and effects, adding them equally to both channels.
    stereo = levels.instruments * instruments * ducking[:, None] + mono_layers[:, None]
    # Divide by the loudest sample, so it becomes 1.0. Every song then reaches mastering at the
    # same level, whatever the genre gains added up to.
    return stereo / np.abs(stereo).max()


# Writes a float WAV, runs the ffmpeg chain, and returns 16-bit PCM bytes.
def master(stereo: np.ndarray, work_dir: Path) -> bytes:
    raw, done = work_dir / "mix.wav", work_dir / "master.wav"
    # Float WAV, so nothing clips before the mastering chain.
    sf.write(raw, stereo, SAMPLE_RATE, subtype="FLOAT")
    # -y overwrites the output file if it exists, -loglevel error prints only errors, -i is the
    # input file, -af runs MASTERING_CHAIN (EQ, compressor, loudnorm, limiter) as the audio
    # filter, -ar keeps the output at SAMPLE_RATE, and -c:a pcm_s16le writes an ordinary 16-bit
    # WAV. check=True raises if ffmpeg exits with an error, and the timeout kills it if it hangs.
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw),
         "-af", MASTERING_CHAIN, "-ar", str(SAMPLE_RATE), "-c:a", "pcm_s16le", str(done)],
        check=True,
        timeout=MASTER_TIMEOUT_SECONDS,
    )
    return done.read_bytes()
