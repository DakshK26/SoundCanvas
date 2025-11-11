#pragma once

#include <vector>
#include <string>

/**
 * Phase 8: MIDI Pattern Transformation Utilities
 * Functions for modifying MIDI patterns: transpose, velocity, automation
 */

struct MidiNote {
    int note;        // MIDI note number (0-127)
    int velocity;    // Velocity (0-127)
    int startTick;   // Start time in ticks
    int duration;    // Duration in ticks
    int channel;     // MIDI channel (0-15)
};

struct MidiPattern {
    std::vector<MidiNote> notes;
    int lengthInTicks;
    int lengthInBars;
};

/**
 * Transpose all notes in a pattern by semitones
 */
void transposePattern(MidiPattern& pattern, int semitones);

/**
 * Scale velocity of all notes by a factor (0-2)
 * factor < 1.0 = quieter, factor > 1.0 = louder
 */
void scaleVelocity(MidiPattern& pattern, float factor);

/**
 * Thin out notes based on energy (remove notes to reduce density)
 * keepRatio: 0.0 = remove all, 1.0 = keep all
 */
void thinNotes(MidiPattern& pattern, float keepRatio);

/**
 * Apply humanization: slight random timing and velocity variations
 */
void humanize(MidiPattern& pattern, int timingVariance, int velocityVariance);

/**
 * Generate automation curve for filter cutoff sweep (build → drop)
 * Returns array of cutoff values (0-127) for each bar
 */
std::vector<int> generateFilterSweep(int bars, float startCutoff, float endCutoff);

/**
 * Generate volume automation curve (crescendo/decrescendo)
 */
std::vector<float> generateVolumeRamp(int bars, float startVol, float endVol);

/**
 * Create a simple kick pattern (4-on-the-floor for EDM)
 */
MidiPattern createKickPattern(int bars, int beatsPerBar = 4);

/**
 * Create a hi-hat pattern (16th notes or 8th notes)
 */
MidiPattern createHiHatPattern(int bars, bool sixteenths = true);

/**
 * Create a snare pattern (backbeat on 2 and 4)
 */
MidiPattern createSnarePattern(int bars);

/**
 * Create a simple bass pattern based on scale
 */
MidiPattern createBassPattern(int bars, int rootNote, int scaleType, float complexity);
