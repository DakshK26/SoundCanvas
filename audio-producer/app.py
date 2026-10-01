"""The audio-producer service. The worker (api/src/serviceClients.ts) POSTs the MIDI file that
cpp-core/src/Composer.cpp wrote to /render?genre={genre} and gets back a mastered WAV.
This file is only the HTTP side: it checks the request and picks the status code. midi.py reads
the MIDI and render.py turns it into audio."""
from fastapi import Body, FastAPI, HTTPException, Response

from drums import KITS
from midi import parse_midi
from render import render_song

MAX_MIDI_BYTES = 1024 * 1024  # 1 MiB cap on the upload, so a huge body is refused before parsing.

app = FastAPI()


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
