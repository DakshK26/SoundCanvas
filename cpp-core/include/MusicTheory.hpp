// music theory cheat sheet for the composer. all standard theory / General MIDI spec stuff,
// I just wrote down where each number comes from so I don't forget

#pragma once

#include <vector>

namespace music {

// ---- timing ----

// midi time is in "ticks". 480/beat is common, divides into 8ths, 16ths AND triplets
constexpr int TICKS_PER_BEAT = 480;

// everything is 4/4
constexpr int BEATS_PER_BAR = 4;

// patterns are 16 steps per bar like a drum machine (1 step = 16th note)
constexpr int STEPS_PER_BAR = 16;

constexpr int TICKS_PER_BAR = TICKS_PER_BEAT * BEATS_PER_BAR;
constexpr int TICKS_PER_STEP = TICKS_PER_BAR / STEPS_PER_BAR;

// ---- scales ----
// semitones from the root. whole step = 2, half step = 1

// major: W W H W W W H -> happy/bright
const std::vector<int> MAJOR_SCALE = {0, 2, 4, 5, 7, 9, 11};

// natural minor: W H W W H W W -> dark
const std::vector<int> MINOR_SCALE = {0, 2, 3, 5, 7, 8, 10};

// dorian = minor w/ a raised 6th. moody but not sad, used a lot in house
const std::vector<int> DORIAN_SCALE = {0, 2, 3, 5, 7, 9, 10};

// ---- progressions ----
// scale degrees counted from 0 (so 0 = I/i, 4 = V, etc)

// I V vi IV - THE pop progression (let it be, someone like you, ...)
const std::vector<int> POP_PROGRESSION = {0, 4, 5, 3};

// vi IV I V - same 4 chords but start on the minor one. very EDM anthem
const std::vector<int> ANTHEM_PROGRESSION = {5, 3, 0, 4};

// i VI III VII - the "epic" minor one from trance / movie trailers
const std::vector<int> EPIC_MINOR_PROGRESSION = {0, 5, 2, 6};

// i iv v i - simple minor loop that keeps coming back home. synthwave-y
const std::vector<int> MINOR_LOOP_PROGRESSION = {0, 3, 4, 0};

// ---- GM drums ----
// channel 10 is always drums in General MIDI (index 9 bc 0-based!). note number = which drum

constexpr int DRUM_CHANNEL = 9;
constexpr int KICK = 36;        // Bass Drum 1
constexpr int SNARE = 38;       // Acoustic Snare
constexpr int CLAP = 39;        // Hand Clap
constexpr int CLOSED_HAT = 42;  // Closed Hi-Hat
constexpr int OPEN_HAT = 46;    // Open Hi-Hat
constexpr int LOW_TOM = 41;     // Low Floor Tom (using it as a fake timpani for cinematic)
constexpr int CRASH = 49;       // Crash Cymbal 1

// ---- GM instruments ----
// program numbers, 0-based. (gotcha: most GM tables online are 1-based, subtract 1)

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

// ---- pitch ----

// 48 = C3. roots go C3..B3 (48-59) so bass (octave down) + lead (octave up) don't get silly high/low
constexpr int LOWEST_ROOT_NOTE = 48;
constexpr int SEMITONES_PER_OCTAVE = 12;

}  // namespace music
