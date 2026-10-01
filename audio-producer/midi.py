"""Reads the MIDI file cpp-core/src/Composer.cpp writes, using mido. app.py turns the request body
into a MidiFile with parse_midi. render.py takes the drum hits and section markers from
read_events, and gives fluidsynth the copy from without_drums."""
import io

import mido

DRUM_CHANNEL = 9  # GM channel 10, 0-based. Same value as DRUM_CHANNEL in MusicTheory.hpp.


def parse_midi(midi_bytes: bytes) -> mido.MidiFile:
    # mido wants a file, so the bytes are wrapped in an in-memory one.
    try:
        return mido.MidiFile(file=io.BytesIO(midi_bytes))
    except Exception as error:  # mido raises several different errors for broken files
        # One error type, so the /render route in app.py can turn it into a 400.
        raise ValueError(f"Invalid MIDI file: {error}") from error


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
