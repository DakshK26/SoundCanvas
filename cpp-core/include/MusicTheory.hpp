// The music theory numbers the composer uses: timing, scales, chord progressions and the
// General MIDI drum and instrument numbers. Header only. GenreTemplate.cpp builds the recipes
// from these, and Composer.cpp and SongPlanner.cpp use the timing and note values.
#pragma once

#include <vector>

namespace music {

// Timing. Every position in the MIDI file is a count of ticks.
constexpr int TICKS_PER_BEAT = 480;  // divides evenly into 8ths, 16ths and triplets
constexpr int BEATS_PER_BAR = 4;
constexpr int STEPS_PER_BAR = 16;  // one step is a 16th note

constexpr int TICKS_PER_BAR = TICKS_PER_BEAT * BEATS_PER_BAR;  // 1920
constexpr int TICKS_PER_STEP = TICKS_PER_BAR / STEPS_PER_BAR;  // 120

// Semitones from the root.
const std::vector<int> MAJOR_SCALE = {0, 2, 4, 5, 7, 9, 11};   // bright, used by EDM_CHILL
const std::vector<int> MINOR_SCALE = {0, 2, 3, 5, 7, 8, 10};   // darker, EDM_DROP and CINEMATIC
const std::vector<int> DORIAN_SCALE = {0, 2, 3, 5, 7, 9, 10};  // minor with a raised 6th, HOUSE

// Scale degrees from 0, so 0 is I and 4 is V.
const std::vector<int> POP_PROGRESSION = {0, 4, 5, 3};         // I V vi IV in a major scale
const std::vector<int> ANTHEM_PROGRESSION = {5, 3, 0, 4};      // POP's chords, starting on degree 5
const std::vector<int> EPIC_MINOR_PROGRESSION = {0, 5, 2, 6};  // i VI III VII in a minor scale

// GM drums are on channel 10, which is 9 counting from 0.
// The note numbers must match audio-producer/drums.py.
constexpr int DRUM_CHANNEL = 9;
constexpr int KICK = 36;        // must match KICK in audio-producer/drums.py
constexpr int SNARE = 38;       // must match SNARE in audio-producer/drums.py
constexpr int CLAP = 39;        // must match CLAP in audio-producer/drums.py
constexpr int CLOSED_HAT = 42;  // must match CLOSED_HAT in audio-producer/drums.py
constexpr int OPEN_HAT = 46;    // must match OPEN_HAT in audio-producer/drums.py
constexpr int LOW_TOM = 41;     // must match LOW_TOM in audio-producer/drums.py
constexpr int CRASH = 49;       // must match CRASH in audio-producer/drums.py

// GM program numbers counted from 0; most GM tables online count from 1.
constexpr int ACOUSTIC_PIANO = 0;
constexpr int ELECTRIC_PIANO = 4;
constexpr int FINGERED_BASS = 33;
constexpr int SYNTH_BASS = 38;
constexpr int STRINGS = 48;
constexpr int SYNTH_BRASS = 62;
constexpr int SQUARE_LEAD = 80;
constexpr int SAW_LEAD = 81;
constexpr int WARM_PAD = 89;
constexpr int POLYSYNTH_PAD = 90;
constexpr int CHOIR_PAD = 91;

// Pitch range for the song's key.
constexpr int LOWEST_ROOT_NOTE = 48;  // C3; roots span C3 to B3
constexpr int SEMITONES_PER_OCTAVE = 12;

}  // namespace music
