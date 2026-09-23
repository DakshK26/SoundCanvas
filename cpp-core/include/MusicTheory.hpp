// Music constants used by the composer, each with a note on where it comes from.
// Everything here is standard music theory or the General MIDI (GM) spec.
#pragma once

#include <vector>

namespace music {

// ---- Timing -----------------------------------------------------------------

// MIDI measures time in "ticks". 480 ticks per beat is a common resolution
// that divides evenly into 8th notes, 16th notes, and triplets.
constexpr int TICKS_PER_BEAT = 480;

// Every genre here is in 4/4 time: 4 beats per bar.
constexpr int BEATS_PER_BAR = 4;

// Rhythm patterns are written as 16 steps per bar (one step = a 16th note).
constexpr int STEPS_PER_BAR = 16;

constexpr int TICKS_PER_BAR = TICKS_PER_BEAT * BEATS_PER_BAR;
constexpr int TICKS_PER_STEP = TICKS_PER_BAR / STEPS_PER_BAR;

// ---- Scales -----------------------------------------------------------------
// A scale is listed as semitone distances from its root note.
// A "whole step" is 2 semitones and a "half step" is 1.

// Major: whole, whole, half, whole, whole, whole, half. Bright and happy.
const std::vector<int> MAJOR_SCALE = {0, 2, 4, 5, 7, 9, 11};

// Natural minor: whole, half, whole, whole, half, whole, whole. Dark and serious.
const std::vector<int> MINOR_SCALE = {0, 2, 3, 5, 7, 8, 10};

// Dorian: natural minor with a raised 6th note. Moody but not sad; common in house.
const std::vector<int> DORIAN_SCALE = {0, 2, 3, 5, 7, 9, 10};

// Lydian: major with a raised 4th note. Dreamy and floating; common in film scores.
const std::vector<int> LYDIAN_SCALE = {0, 2, 4, 6, 7, 9, 11};

// ---- Chord progressions -----------------------------------------------------
// Listed as scale degrees, counted from 0 (0 = the root chord, "I" or "i").

// I - V - vi - IV: the most common pop progression ("Let It Be", "Someone Like You").
const std::vector<int> POP_PROGRESSION = {0, 4, 5, 3};

// vi - IV - I - V: the same four chords starting on the minor chord. Uplifting in EDM.
const std::vector<int> ANTHEM_PROGRESSION = {5, 3, 0, 4};

// i - VI - III - VII: the standard "epic" minor progression in trance and film music.
const std::vector<int> EPIC_MINOR_PROGRESSION = {0, 5, 2, 6};

// i - iv - v - i: a simple minor loop that keeps returning home. Common in synthwave.
const std::vector<int> MINOR_LOOP_PROGRESSION = {0, 3, 4, 0};

// ---- General MIDI drums -----------------------------------------------------
// GM Level 1 reserves channel 10 (index 9) for drums; each note number is a sound.

constexpr int DRUM_CHANNEL = 9;
constexpr int KICK = 36;        // Bass Drum 1
constexpr int SNARE = 38;       // Acoustic Snare
constexpr int CLAP = 39;        // Hand Clap
constexpr int CLOSED_HAT = 42;  // Closed Hi-Hat
constexpr int OPEN_HAT = 46;    // Open Hi-Hat
constexpr int LOW_TOM = 41;     // Low Floor Tom (used as a timpani-like hit)
constexpr int CRASH = 49;       // Crash Cymbal 1

// ---- General MIDI instruments -----------------------------------------------
// Program numbers from the GM Level 1 instrument list, counted from 0.

constexpr int ACOUSTIC_PIANO = 0;
constexpr int ELECTRIC_PIANO = 4;
constexpr int FINGERED_BASS = 33;
constexpr int SYNTH_BASS = 38;
constexpr int STRINGS = 48;
constexpr int SYNTH_BRASS = 62;
constexpr int SQUARE_LEAD = 80;
constexpr int SAW_LEAD = 81;
constexpr int NEW_AGE_PAD = 88;
constexpr int WARM_PAD = 89;
constexpr int POLYSYNTH_PAD = 90;
constexpr int CHOIR_PAD = 91;

// ---- Pitch ------------------------------------------------------------------

// MIDI note 48 is C3. Song roots sit between C3 and B3 (48 to 59), so the bass
// (one octave lower) and the lead (one octave higher) stay in a comfortable range.
constexpr int LOWEST_ROOT_NOTE = 48;
constexpr int SEMITONES_PER_OCTAVE = 12;

}  // namespace music
