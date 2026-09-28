"""audio-producer tests. don't need fluidsynth or ffmpeg installed - only tests my code:
midi handling, synth drums/fx, the mix, and the /render input checks (which run before
either tool gets called)

from repo root: python -m unittest discover -s audio-producer/tests -v
"""
import sys
import unittest
from pathlib import Path

import mido
import numpy as np
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import DRUM_CHANNEL, MAX_MIDI_BYTES, parse_midi, read_events, render, without_drums  # noqa: E402
from drums import KICK, KITS, render_drums  # noqa: E402
from fx import SWEEP_SECONDS, render_fx  # noqa: E402
from mixer import MIXES, mix, sidechain  # noqa: E402
from synth import SAMPLE_RATE  # noqa: E402

TICKS_PER_BEAT = 480  # no tempo msg -> mido assumes 120bpm -> 1 beat = 0.5s


def song() -> mido.MidiFile:
    """tiny song: bass note, kick on beat 2, "drop" marker on beat 3, all 1 track"""
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
        hits, markers = read_events(song())
        self.assertEqual(hits, [(0.5, KICK, 127)])
        self.assertEqual(markers, [(1.0, "drop")])

    def test_strips_drums_without_moving_later_events(self):
        stripped = without_drums(song())
        channels = [msg.channel for msg in stripped if hasattr(msg, "channel")]
        self.assertNotIn(DRUM_CHANNEL, channels)
        self.assertEqual(sum(msg.time for msg in stripped), sum(msg.time for msg in song()))

    def test_rejects_bytes_that_are_not_midi(self):
        with self.assertRaises(ValueError):
            parse_midi(b"not a midi file")


class RenderEndpointTest(unittest.TestCase):
    """these HAVE to be 400/413 not 500, or the worker retries something that'll never work"""

    def assert_status(self, status: int, genre: str, body: bytes):
        with self.assertRaises(HTTPException) as caught:
            render(genre, body)
        self.assertEqual(caught.exception.status_code, status)

    def test_rejects_an_unknown_genre(self):
        self.assert_status(400, "JAZZ", b"MThd")

    def test_rejects_an_oversized_file(self):
        self.assert_status(413, "HOUSE", b"\0" * (MAX_MIDI_BYTES + 1))

    def test_rejects_a_corrupt_file(self):
        self.assert_status(400, "HOUSE", b"MThd garbage")


class SoundTest(unittest.TestCase):
    LENGTH = 2 * SAMPLE_RATE

    def test_drums_land_on_their_hits_and_render_the_same_every_time(self):
        for genre in KITS:
            track = render_drums([(1.0, KICK, 127)], genre, self.LENGTH)
            self.assertTrue(np.all(track[: SAMPLE_RATE] == 0), genre)  # nothing before the hit
            self.assertGreater(np.abs(track[SAMPLE_RATE:]).max(), 0.5, genre)
            np.testing.assert_array_equal(track, render_drums([(1.0, KICK, 127)], genre, self.LENGTH))

    def test_a_drop_gets_a_riser_before_it_and_an_impact_after(self):
        track = render_fx([(1.5, "drop")], 3 * SAMPLE_RATE)
        riser_start = int((1.5 - SWEEP_SECONDS) * SAMPLE_RATE)
        self.assertTrue(np.all(track[: max(riser_start, 0)] == 0))
        self.assertGreater(np.abs(track[int(1.4 * SAMPLE_RATE): int(1.5 * SAMPLE_RATE)]).max(), 0)
        self.assertGreater(np.abs(track[int(1.5 * SAMPLE_RATE):]).max(), 0)

    def test_sidechain_ducks_at_each_kick_and_recovers(self):
        curve = sidechain([0.5], self.LENGTH, depth=0.6)
        kick = int(0.5 * SAMPLE_RATE)
        self.assertEqual(curve[kick - 1], 1.0)
        self.assertAlmostEqual(curve[kick], 0.4)
        self.assertGreater(curve[kick + int(0.3 * SAMPLE_RATE)], 0.97)

    def test_mix_is_stereo_and_peaks_at_full_scale(self):
        rng = np.random.default_rng(1)
        instruments = 0.1 * rng.standard_normal((self.LENGTH, 2))
        drums, fx = 0.3 * rng.standard_normal(self.LENGTH), np.zeros(self.LENGTH)
        for genre in MIXES:
            stereo = mix(instruments, drums, fx, [0.5], genre)
            self.assertEqual(stereo.shape, (self.LENGTH, 2))
            self.assertAlmostEqual(np.abs(stereo).max(), 1.0)


if __name__ == "__main__":
    unittest.main()
