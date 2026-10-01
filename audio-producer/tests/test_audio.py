"""Tests for the parts written here: MIDI handling, the error codes, and the numpy sound code.
fluidsynth and ffmpeg aren't called, so these run without them installed. They import app.py,
drums.py, fx.py, mixer.py and synth.py directly."""
import sys
import unittest
from pathlib import Path

import mido
import numpy as np
from fastapi import HTTPException

# Lets the tests import the service modules from the audio-producer folder one level up.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import DRUM_CHANNEL, MAX_MIDI_BYTES, parse_midi, read_events, render, without_drums  # noqa: E402
from drums import KICK, KITS, render_drums  # noqa: E402
from fx import SWEEP_SECONDS, render_fx  # noqa: E402
from mixer import MIXES, mix, sidechain  # noqa: E402
from synth import SAMPLE_RATE  # noqa: E402

# With no tempo message mido assumes 120 bpm, so a beat is 0.5 s.
TICKS_PER_BEAT = 480


# A bass note at 0 s, a kick at 0.5 s, a drop marker at 1 s, and the bass note ending at 1.5 s.
# Each time= is ticks since the previous message, so every message is one beat after the last.
def song() -> mido.MidiFile:
    track = mido.MidiTrack([
        mido.Message("note_on", channel=0, note=40, velocity=90, time=0),
        mido.Message("note_on", channel=DRUM_CHANNEL, note=KICK, velocity=127, time=TICKS_PER_BEAT),
        mido.MetaMessage("marker", text="drop", time=TICKS_PER_BEAT),
        mido.Message("note_off", channel=0, note=40, velocity=0, time=TICKS_PER_BEAT),
    ])
    midi = mido.MidiFile(ticks_per_beat=TICKS_PER_BEAT)
    midi.tracks.append(track)
    return midi


class MidiHandlingTest(unittest.TestCase):
    def test_reads_drum_hits_and_markers_in_seconds(self):
        """read_events in app.py adds up the delta times, so hits and markers come out at their
        absolute time in seconds, and only drum-channel notes count as hits."""
        hits, markers = read_events(song())
        self.assertEqual(hits, [(0.5, KICK, 127)])
        self.assertEqual(markers, [(1.0, "drop")])

    def test_strips_drums_without_moving_later_events(self):
        """without_drums in app.py removes the drum channel and hands the removed ticks on to
        the next message, so the total length of the song doesn't change."""
        stripped = without_drums(song())
        channels = [msg.channel for msg in stripped if hasattr(msg, "channel")]
        self.assertNotIn(DRUM_CHANNEL, channels)
        self.assertEqual(sum(msg.time for msg in stripped), sum(msg.time for msg in song()))

    def test_rejects_bytes_that_are_not_midi(self):
        """parse_midi in app.py turns any mido error into a ValueError."""
        with self.assertRaises(ValueError):
            parse_midi(b"not a midi file")


class RenderEndpointTest(unittest.TestCase):
    """These must be 4xx, not 500, or the worker retries them."""

    # Calls the /render handler in app.py directly and checks the HTTP status it raises.
    def assert_status(self, status: int, genre: str, body: bytes):
        with self.assertRaises(HTTPException) as caught:
            render(genre, body)
        self.assertEqual(caught.exception.status_code, status)

    def test_rejects_an_unknown_genre(self):
        """render in app.py answers 400 for a genre that isn't a key of KITS in drums.py."""
        self.assert_status(400, "JAZZ", b"MThd")

    def test_rejects_an_oversized_file(self):
        """render in app.py answers 413 for a body over MAX_MIDI_BYTES."""
        self.assert_status(413, "HOUSE", b"\0" * (MAX_MIDI_BYTES + 1))

    def test_rejects_a_corrupt_file(self):
        """render in app.py answers 400 when parse_midi can't read the body. "MThd" is how a
        real MIDI file starts, so this checks a file that only looks valid at first."""
        self.assert_status(400, "HOUSE", b"MThd garbage")


class SoundTest(unittest.TestCase):
    LENGTH = 2 * SAMPLE_RATE

    def test_drums_land_on_their_hits_and_render_the_same_every_time(self):
        """render_drums in drums.py puts each hit at its time and nowhere before it, for every
        kit, and the fixed NOISE_SEED in synth.py makes two renders identical."""
        for genre in KITS:
            track = render_drums([(1.0, KICK, 127)], genre, self.LENGTH)
            self.assertTrue(np.all(track[: SAMPLE_RATE] == 0), genre)
            self.assertGreater(np.abs(track[SAMPLE_RATE:]).max(), 0.5, genre)
            np.testing.assert_array_equal(track, render_drums([(1.0, KICK, 127)], genre, self.LENGTH))

    def test_a_drop_gets_a_riser_before_it_and_an_impact_after(self):
        """render_fx in fx.py puts the riser just before a "drop" marker and the impact on it.
        The drop here is at 1.5 s, under SWEEP_SECONDS, so the riser start is clamped to 0."""
        track = render_fx([(1.5, "drop")], 3 * SAMPLE_RATE)
        riser_start = int((1.5 - SWEEP_SECONDS) * SAMPLE_RATE)
        self.assertTrue(np.all(track[: max(riser_start, 0)] == 0))
        self.assertGreater(np.abs(track[int(1.4 * SAMPLE_RATE): int(1.5 * SAMPLE_RATE)]).max(), 0)
        self.assertGreater(np.abs(track[int(1.5 * SAMPLE_RATE):]).max(), 0)

    def test_sidechain_ducks_at_each_kick_and_recovers(self):
        """sidechain in mixer.py leaves the volume at 1 before a kick, drops it to 1 - depth on
        the kick, and lets it climb most of the way back 0.3 s later."""
        curve = sidechain([0.5], self.LENGTH, depth=0.6)
        kick = int(0.5 * SAMPLE_RATE)
        self.assertEqual(curve[kick - 1], 1.0)
        self.assertAlmostEqual(curve[kick], 0.4)
        self.assertGreater(curve[kick + int(0.3 * SAMPLE_RATE)], 0.97)

    def test_mix_is_stereo_and_peaks_at_full_scale(self):
        """mix in mixer.py keeps fluidsynth's (samples, 2) stereo shape while adding the mono
        layers, and normalizes so the loudest sample is exactly 1.0, for every genre in MIXES."""
        rng = np.random.default_rng(1)
        instruments = 0.1 * rng.standard_normal((self.LENGTH, 2))
        drums, fx = 0.3 * rng.standard_normal(self.LENGTH), np.zeros(self.LENGTH)
        for genre in MIXES:
            stereo = mix(instruments, drums, fx, [0.5], genre)
            self.assertEqual(stereo.shape, (self.LENGTH, 2))
            self.assertAlmostEqual(np.abs(stereo).max(), 1.0)


if __name__ == "__main__":
    unittest.main()
