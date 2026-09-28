"""audio-producer - cpp-core's midi -> finished wav

POST /render?genre=HOUSE, body = the .mid bytes -> audio/wav

pipeline:
  1. fluidsynth plays bass/chords/lead/pad w/ a General MIDI soundfont
  2. drums.py synthesizes the drums itself (channel 10) instead of the soundfont's one kit,
     so each genre gets its own drum sound
  3. fx.py puts risers/impacts on the section markers
  4. mixer.py balances the 3 stems + masters w/ ffmpeg
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
DRUM_CHANNEL = 9  # = channel 10 (0-based), GM drums
MAX_MIDI_BYTES = 1024 * 1024  # real songs are < 20KB, anything near 1MB didn't come from cpp-core
# fluidsynth does a 2 min song in a few sec. still going after 60s = it's stuck
RENDER_TIMEOUT_SECONDS = 60

app = FastAPI()


def read_events(midi: mido.MidiFile):
    """-> drum hits [(sec, note, vel)] and markers [(sec, name)]"""
    hits, markers, seconds = [], [], 0.0
    # learned: iterating the MidiFile (not a track) merges all tracks + msg.time is in SECONDS not ticks
    for msg in midi:
        seconds += msg.time
        if msg.type == "note_on" and msg.channel == DRUM_CHANNEL and msg.velocity > 0:
            hits.append((seconds, msg.note, msg.velocity))
        elif msg.type == "marker":
            markers.append((seconds, msg.text))
    return hits, markers


def without_drums(midi: mido.MidiFile) -> mido.MidiFile:
    """copy of the song minus channel 10, so fluidsynth only plays the instruments"""
    stripped = mido.MidiFile(ticks_per_beat=midi.ticks_per_beat)
    for track in midi.tracks:
        kept, skipped_ticks = mido.MidiTrack(), 0
        for msg in track:
            if getattr(msg, "channel", None) == DRUM_CHANNEL:
                # gotcha: times are deltas. carry the dropped msg's time forward or everything after shifts earlier
                skipped_ticks += msg.time
                continue
            kept.append(msg.copy(time=msg.time + skipped_ticks))
            skipped_ticks = 0
        stripped.tracks.append(kept)
    return stripped


def render_instruments(midi: mido.MidiFile, work_dir: Path):
    """fluidsynth -> stereo numpy array. goes thru temp files bc fluidsynth only does files"""
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
    """bytes -> MidiFile, or ValueError if it's not valid midi"""
    try:
        return mido.MidiFile(file=io.BytesIO(midi_bytes))
    except Exception as error:  # mido throws OSError/EOFError/KeyError/... depending how broken it is, so catch all
        raise ValueError(f"Invalid MIDI file: {error}") from error


def render_song(midi: mido.MidiFile, genre: str) -> bytes:
    """whole pipeline -> mastered wav bytes"""
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
    # NOTE: plain def on purpose, NOT async def. fastapi runs sync handlers in a threadpool.
    # as async def the multi-second render would block the event loop -> /health times out
    # -> ECS thinks the container is dead and kills it mid-render
    # 400 = worker won't retry, anything else -> 500 -> retried
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
