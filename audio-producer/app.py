"""audio-producer: turns cpp-core's MIDI into a finished WAV song.

POST /render?genre=HOUSE with the MIDI file as the request body returns audio/wav.

Steps:
  1. FluidSynth plays the pitched parts (bass, chords, lead, pad) with a General MIDI soundfont.
  2. drums.py synthesizes the drum notes (MIDI channel 10), so they get genre-specific sounds.
  3. fx.py adds risers and impacts at the section markers.
  4. mixer.py balances the three tracks and masters them with ffmpeg.
"""
import io
import os
import subprocess
import tempfile
from pathlib import Path

import mido
import soundfile as sf
from fastapi import Body, FastAPI, HTTPException, Response

from drums import KICK, KITS, render_drums
from fx import render_fx
from mixer import master, mix
from synth import SAMPLE_RATE

SOUNDFONT = os.environ.get("SOUNDFONT_PATH", "/usr/share/sounds/sf2/FluidR3_GM.sf2")
DRUM_CHANNEL = 9  # MIDI channel 10, counted from zero; reserved for percussion
MAX_MIDI_BYTES = 1024 * 1024  # a composed song is under 20 KB; anything near 1 MB is not ours
# FluidSynth renders a two-minute song in a few seconds; one still running after a minute is hung.
RENDER_TIMEOUT_SECONDS = 60

app = FastAPI()


def read_events(midi: mido.MidiFile):
    """Returns the drum hits (seconds, note, velocity) and section markers (seconds, name)."""
    hits, markers, seconds = [], [], 0.0
    for msg in midi:  # iterating a MidiFile merges tracks and gives delta times in seconds
        seconds += msg.time
        if msg.type == "note_on" and msg.channel == DRUM_CHANNEL and msg.velocity > 0:
            hits.append((seconds, msg.note, msg.velocity))
        elif msg.type == "marker":
            markers.append((seconds, msg.text))
    return hits, markers


def without_drums(midi: mido.MidiFile) -> mido.MidiFile:
    """A copy of the song with the drum channel removed, for FluidSynth to render."""
    stripped = mido.MidiFile(ticks_per_beat=midi.ticks_per_beat)
    for track in midi.tracks:
        kept, skipped_ticks = mido.MidiTrack(), 0
        for msg in track:
            if getattr(msg, "channel", None) == DRUM_CHANNEL:
                skipped_ticks += msg.time  # keep later events at the same moment
                continue
            kept.append(msg.copy(time=msg.time + skipped_ticks))
            skipped_ticks = 0
        stripped.tracks.append(kept)
    return stripped


def render_instruments(midi: mido.MidiFile, work_dir: Path):
    """Renders the pitched parts to a stereo array with FluidSynth."""
    midi_path, wav_path = work_dir / "instruments.mid", work_dir / "instruments.wav"
    without_drums(midi).save(midi_path)
    subprocess.run(
        ["fluidsynth", "-ni", "-q", "-r", str(SAMPLE_RATE), "-F", str(wav_path),
         SOUNDFONT, str(midi_path)],
        check=True,
        timeout=RENDER_TIMEOUT_SECONDS,
    )
    audio, _ = sf.read(wav_path)
    return audio


def parse_midi(midi_bytes: bytes) -> mido.MidiFile:
    """Reads a MIDI file, raising ValueError if the bytes are not one."""
    try:
        return mido.MidiFile(file=io.BytesIO(midi_bytes))
    except Exception as error:  # mido raises OSError, EOFError, KeyError... depending on the damage
        raise ValueError(f"Invalid MIDI file: {error}") from error


def render_song(midi: mido.MidiFile, genre: str) -> bytes:
    """Runs the whole pipeline and returns the mastered WAV file."""
    hits, markers = read_events(midi)
    with tempfile.TemporaryDirectory() as tmp:
        work_dir = Path(tmp)
        instruments = render_instruments(midi, work_dir)
        length = len(instruments)
        drums = render_drums(hits, genre, length)
        fx = render_fx(markers, length)
        kick_times = [seconds for seconds, note, _ in hits if note == KICK]
        return master(mix(instruments, drums, fx, kick_times, genre), work_dir)


@app.post("/render")
def render(genre: str, midi: bytes = Body(media_type="audio/midi")) -> Response:
    # A plain `def`, not `async def`: FastAPI runs it on a worker thread, so a render that
    # takes seconds of CPU does not freeze the server (and its /health check) meanwhile.
    # 400 tells the worker retrying is pointless; any other failure is a 500 and gets retried.
    if genre not in KITS:
        raise HTTPException(400, f"Unknown genre {genre}")
    if len(midi) > MAX_MIDI_BYTES:
        raise HTTPException(413, "MIDI file too large")
    try:
        song = parse_midi(midi)
    except ValueError as error:
        raise HTTPException(400, str(error)) from error
    return Response(render_song(song, genre), media_type="audio/wav")


@app.get("/health")
def health():
    return {"ok": True}
