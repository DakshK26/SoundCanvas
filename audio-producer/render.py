"""Turns a parsed MIDI file into the finished WAV. fluidsynth plays the pitched instruments, drums.py
and fx.py make the drums and effects in numpy, and mixer.py mixes them and masters the result
with ffmpeg. app.py calls render_song once per /render request."""
import os
import subprocess
import tempfile
from pathlib import Path

import mido
import soundfile as sf

from drums import KICK, render_drums
from fx import render_fx
from midi import read_events, without_drums
from mixer import master, mix
from synth import SAMPLE_RATE

# The Dockerfile installs fluid-soundfont-gm, which puts the soundfont at this default path.
# The environment variable lets it be pointed somewhere else when running outside the container.
SOUNDFONT = os.environ.get("SOUNDFONT_PATH", "/usr/share/sounds/sf2/FluidR3_GM.sf2")
RENDER_TIMEOUT_SECONDS = 60


# fluidsynth plays the MIDI through a General MIDI soundfont into a WAV file.
def render_instruments(midi: mido.MidiFile, work_dir: Path):
    midi_path, wav_path = work_dir / "instruments.mid", work_dir / "instruments.wav"
    without_drums(midi).save(midi_path)
    # -n: no MIDI input device, -i: no interactive shell, -q: quiet, -r: sample rate,
    # -F: render straight to this file instead of the sound card. check=True raises if fluidsynth
    # fails, and the timeout stops a stuck render from holding the request forever.
    subprocess.run(
        ["fluidsynth", "-ni", "-q", "-r", str(SAMPLE_RATE), "-F", str(wav_path),
         SOUNDFONT, str(midi_path)],
        check=True,
        timeout=RENDER_TIMEOUT_SECONDS,
    )
    # sf.read gives (samples, sample_rate). The samples are a (length, 2) float array, left and right.
    audio, _ = sf.read(wav_path)
    return audio


# The instruments set the length. Drums and effects are made at that same length so the three
# arrays can be added together.
def render_song(midi: mido.MidiFile, genre: str) -> bytes:
    # Read drum hits and section markers before the drums are stripped out.
    hits, markers = read_events(midi)
    # The temporary folder holds the .mid and .wav files fluidsynth and ffmpeg need, and is
    # deleted when the block ends, even if a step fails.
    with tempfile.TemporaryDirectory() as tmp:
        work_dir = Path(tmp)
        # Strip the drum channel and render the pitched parts with FluidSynth.
        instruments = render_instruments(midi, work_dir)
        length = len(instruments)
        # Synthesize the drums and effects in numpy at the same length.
        drums = render_drums(hits, genre, length)
        fx = render_fx(markers, length)
        # The kick times drive the sidechain ducking in mixer.py.
        kick_times = [seconds for seconds, note, _ in hits if note == KICK]
        # Mix at the genre's levels, then master with ffmpeg and return the WAV bytes.
        return master(mix(instruments, drums, fx, kick_times, genre), work_dir)
