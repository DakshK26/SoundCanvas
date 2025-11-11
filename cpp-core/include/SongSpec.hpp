#pragma once

#include <vector>
#include <string>
#include "ImageFeatures.hpp"
#include "AudioEngine.hpp"

/**
 * Phase 7: Multi-track song composition system
 * Transforms image features → structured MIDI song with multiple instruments
 */

enum class AmbienceType {
    NONE = 0,
    OCEAN = 1,
    RAIN = 2,
    FOREST = 3,
    CITY = 4
};

enum class InstrumentPreset {
    SOFT_PAD = 0,    // Warm, sustained synth pad
    KEYS = 1,        // Piano/electric piano
    PLUCK = 2,       // Plucked strings/harp
    BELL = 3         // Bells/mallets/vibraphone
};

enum class GrooveType {
    STRAIGHT = 0,    // Simple, straight beats (4/4, no swing)
    CHILL = 1,       // Laid-back, sparse drums
    DRIVING = 2      // More rhythmic, energetic patterns
};

struct TrackSpec {
    std::string role;         // "drums", "bass", "chords", "melody", "pad"
    InstrumentPreset preset;  // Which instrument type to use
    int midiProgram;          // General MIDI program number (0-127)
    float volume;             // 0-1, controls MIDI velocity scaling
    float complexity;         // 0-1, affects note density/variation
};

struct SectionSpec {
    std::string name;         // "intro", "A", "B", "outro"
    int bars;                 // Number of bars in this section
    float energy;             // 0-1, section-specific energy level
};

struct SongSpec {
    // Global song parameters
    float tempoBpm;           // 40-140 BPM
    int scaleType;            // 0=Major, 1=Minor, 2=Dorian, 3=Lydian
    int rootMidiNote;         // Root note in MIDI (e.g., 60 = C4)
    int totalBars;            // Total song length in bars
    
    // Style & arrangement
    GrooveType groove;        // Rhythm style
    AmbienceType ambience;    // Background atmosphere type
    float moodScore;          // 0-1: how lush/pleasant (affects layering)
    
    // Song structure
    std::vector<SectionSpec> sections;  // Intro, A, B, Outro, etc.
    std::vector<TrackSpec> tracks;      // All instrument tracks
};

/**
 * Convert image features + music parameters into a structured song spec.
 * This is the "music director" that decides arrangement, instrumentation, structure.
 */
SongSpec makeSongSpec(const ImageFeatures& features, const MusicParameters& params);

/**
 * Utility: Convert frequency (Hz) to nearest MIDI note number
 */
int freqToMidiNote(float freq);

/**
 * Utility: Get human-readable name for ambience type
 */
const char* ambienceTypeName(AmbienceType type);

/**
 * Utility: Get human-readable name for instrument preset
 */
const char* instrumentPresetName(InstrumentPreset preset);

/**
 * Utility: Get human-readable name for groove type
 */
const char* grooveTypeName(GrooveType type);
