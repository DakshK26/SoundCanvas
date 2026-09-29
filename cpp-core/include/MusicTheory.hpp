#pragma once

#include <vector>

namespace music {

constexpr int TICKS_PER_BEAT = 480;  // divides evenly into 8ths, 16ths and triplets
constexpr int BEATS_PER_BAR = 4;
constexpr int STEPS_PER_BAR = 16;  // one step is a 16th note

constexpr int TICKS_PER_BAR = TICKS_PER_BEAT * BEATS_PER_BAR;
constexpr int TICKS_PER_STEP = TICKS_PER_BAR / STEPS_PER_BAR;

// Semitones from the root.
const std::vector<int> MAJOR_SCALE = {0, 2, 4, 5, 7, 9, 11};
const std::vector<int> MINOR_SCALE = {0, 2, 3, 5, 7, 8, 10};
const std::vector<int> DORIAN_SCALE = {0, 2, 3, 5, 7, 9, 10};

// Scale degrees from 0, so 0 is I and 4 is V.
const std::vector<int> POP_PROGRESSION = {0, 4, 5, 3};
const std::vector<int> ANTHEM_PROGRESSION = {5, 3, 0, 4};
const std::vector<int> EPIC_MINOR_PROGRESSION = {0, 5, 2, 6};
const std::vector<int> MINOR_LOOP_PROGRESSION = {0, 3, 4, 0};

// GM drums are on channel 10, which is 9 counting from 0.
// The note numbers must match audio-producer/drums.py.
constexpr int DRUM_CHANNEL = 9;
constexpr int KICK = 36;
constexpr int SNARE = 38;
constexpr int CLAP = 39;
constexpr int CLOSED_HAT = 42;
constexpr int OPEN_HAT = 46;
constexpr int LOW_TOM = 41;
constexpr int CRASH = 49;

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

constexpr int LOWEST_ROOT_NOTE = 48;  // C3; roots span C3 to B3
constexpr int SEMITONES_PER_OCTAVE = 12;

}  // namespace music
