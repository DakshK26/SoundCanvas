"""The audio-producer service. The worker (api/src/serviceClients.ts) POSTs the MIDI file that
cpp-core/src/Composer.cpp wrote to /render?genre={genre} and gets back a mastered WAV.
fluidsynth plays the pitched instruments, drums.py and fx.py make the drums and effects in numpy,
and mixer.py mixes them and masters the result with ffmpeg."""
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

# The Dockerfile installs fluid-soundfont-gm, which puts the soundfont at this default path.
# The environment variable lets it be pointed somewhere else when running outside the container.
SOUNDFONT = os.environ.get("SOUNDFONT_PATH", "/usr/share/sounds/sf2/FluidR3_GM.sf2")
DRUM_CHANNEL = 9  # GM channel 10, 0-based. Same value as DRUM_CHANNEL in MusicTheory.hpp.
MAX_MIDI_BYTES = 1024 * 1024  # 1 MiB cap on the upload, so a huge body is refused before parsing.
RENDER_TIMEOUT_SECONDS = 60

app = FastAPI()


def read_events(midi: mido.MidiFile):
    """Drum hits as (seconds, note, velocity) and markers as (seconds, name)."""
    hits, markers, seconds = [], [], 0.0
    # Iterating the MidiFile merges the tracks into one time-ordered stream, and mido turns each
    # message's tick delta into seconds using ticks_per_beat and the tempo message. msg.time is
    # still a delta (time since the previous message), so adding them up gives the absolute time.
    for msg in midi:
        seconds += msg.time
        # By MIDI convention a note_on with velocity 0 means note off, so it isn't a hit.
        if msg.type == "note_on" and msg.channel == DRUM_CHANNEL and msg.velocity > 0:
            hits.append((seconds, msg.note, msg.velocity))
        # Composer.cpp writes a marker named after each section ("intro", "build", "drop", ...).
        elif msg.type == "marker":
            markers.append((seconds, msg.text))
    return hits, markers


# fluidsynth only plays the instruments. The drums are made in drums.py, so each genre gets its
# own kit instead of the soundfont's generic one.
def without_drums(midi: mido.MidiFile) -> mido.MidiFile:
    stripped = mido.MidiFile(ticks_per_beat=midi.ticks_per_beat)
    for track in midi.tracks:
        kept, skipped_ticks = mido.MidiTrack(), 0
        for msg in track:
            # Meta messages (tempo, markers) have no channel, so getattr gives None and they stay.
            if getattr(msg, "channel", None) == DRUM_CHANNEL:
                # Inside a track msg.time is in ticks since the previous message. If a drum
                # message is dropped, its ticks are added to the next kept message so that
                # message still lands at the same absolute time.
                skipped_ticks += msg.time
                continue
            kept.append(msg.copy(time=msg.time + skipped_ticks))
            skipped_ticks = 0
        stripped.tracks.append(kept)
    return stripped


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


def parse_midi(midi_bytes: bytes) -> mido.MidiFile:
    # mido wants a file, so the bytes are wrapped in an in-memory one.
    try:
        return mido.MidiFile(file=io.BytesIO(midi_bytes))
    except Exception as error:  # mido raises several different errors for broken files
        # One error type, so render() can turn it into a 400.
        raise ValueError(f"Invalid MIDI file: {error}") from error


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


@app.post("/render")
def render(genre: str, midi: bytes = Body(media_type="audio/midi")) -> Response:
    # genre comes from the query string; the raw MIDI bytes are the request body.
    # Plain def so FastAPI runs it in a thread pool. As async def the render would block
    # /health, and ECS would kill the container mid-render.
    # Validate first. A 4xx tells the worker the input is bad and it should not retry.
    if genre not in KITS:
        raise HTTPException(400, f"Unknown genre {genre}")
    if len(midi) > MAX_MIDI_BYTES:
        raise HTTPException(413, "MIDI file too large")
    try:
        song = parse_midi(midi)
    except ValueError as error:
        raise HTTPException(400, str(error)) from error
    # Anything that fails after this point (fluidsynth, ffmpeg) is a 500, which pipeline.ts retries.
    return Response(render_song(song, genre), media_type="audio/wav")


# The ECS container health check in infra/terraform/ecs.tf calls this and expects a 200.
@app.get("/health")
def health():
    return {"ok": True}
