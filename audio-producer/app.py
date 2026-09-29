"""Renders cpp-core's MIDI to a mastered WAV: POST /render?genre=HOUSE with the .mid bytes."""
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
DRUM_CHANNEL = 9  # GM channel 10, 0-based
MAX_MIDI_BYTES = 1024 * 1024
RENDER_TIMEOUT_SECONDS = 60

app = FastAPI()


def read_events(midi: mido.MidiFile):
    """Drum hits as (seconds, note, velocity) and markers as (seconds, name)."""
    hits, markers, seconds = [], [], 0.0
    # Iterating the MidiFile merges the tracks, and msg.time is in seconds, not ticks.
    for msg in midi:
        seconds += msg.time
        if msg.type == "note_on" and msg.channel == DRUM_CHANNEL and msg.velocity > 0:
            hits.append((seconds, msg.note, msg.velocity))
        elif msg.type == "marker":
            markers.append((seconds, msg.text))
    return hits, markers


def without_drums(midi: mido.MidiFile) -> mido.MidiFile:
    stripped = mido.MidiFile(ticks_per_beat=midi.ticks_per_beat)
    for track in midi.tracks:
        kept, skipped_ticks = mido.MidiTrack(), 0
        for msg in track:
            if getattr(msg, "channel", None) == DRUM_CHANNEL:
                # Times are deltas, so a dropped message's time carries over to the next one.
                skipped_ticks += msg.time
                continue
            kept.append(msg.copy(time=msg.time + skipped_ticks))
            skipped_ticks = 0
        stripped.tracks.append(kept)
    return stripped


def render_instruments(midi: mido.MidiFile, work_dir: Path):
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
    try:
        return mido.MidiFile(file=io.BytesIO(midi_bytes))
    except Exception as error:  # mido raises several different errors for broken files
        raise ValueError(f"Invalid MIDI file: {error}") from error


def render_song(midi: mido.MidiFile, genre: str) -> bytes:
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
    # Plain def so FastAPI runs it in a thread pool. As async def the render would block
    # /health, and ECS would kill the container mid-render.
    # A 4xx tells the worker not to retry.
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
