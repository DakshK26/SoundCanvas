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

// Phase 9: Genre classification for style diversity
enum class Genre {
    EDM_CHILL = 0,   // Ambient/downtempo EDM
    EDM_DROP = 1,    // High-energy EDM with drops
    HOUSE = 2,       // 4-on-the-floor house music
    RAP = 3,         // Hip-hop/trap beats
    RNB = 4          // R&B/neo-soul
};

// Phase 9: Genre-specific musical characteristics
struct GenreProfile {
    Genre genre;
    std::string name;
    
    // Musical ranges
    float minTempo;
    float maxTempo;
    std::vector<int> preferredScaleTypes;  // Indices: 0=Major, 1=Minor, 2=Dorian, 3=Lydian
    
    // Groove & feel
    bool useSwing;           // Apply swing to off-beat notes
    float swingAmount;       // 0.0-0.3 (swing ratio)
    bool heavySidechain;     // Strong pumping effect
    
    // Pattern selection hints
    std::vector<std::string> drumPatternSets;
    std::vector<std::string> chordProgressionSets;
    std::vector<std::string> bassPatternSets;
    std::vector<std::string> leadPatternSets;
    
    // Arrangement tendencies
    int minBars;
    int maxBars;
    bool hasBigDrop;
    bool hasBridge;
};

// Phase 9: Section activity - which tracks are active in which sections
struct SectionActivity {
    bool drums;
    bool bass;
    bool chords;
    bool lead;
    bool pad;
};

// Phase 8: Track role classification for composition engine
enum class TrackRole {
    DRUMS = 0,       // Percussion (kick, snare, hats)
    BASS = 1,        // Low-end foundation
    CHORDS = 2,      // Harmonic content (pads, keys)
    LEAD = 3,        // Melodic hooks
    PAD = 4,         // Atmospheric layer
    FX = 5           // Sound effects / ambience
};

struct TrackSpec {
    TrackRole role;           // Track function in arrangement
    float baseVolume;         // 0-1, base mix level
    float complexity;         // 0-1, affects note density/variation
    int midiChannel;          // MIDI channel (0-15, channel 9 = drums)
    int program;              // General MIDI program number (0-127)
};

struct SectionSpec {
    std::string name;         // "intro", "build", "drop", "break", "outro"
    int bars;                 // Number of bars in this section
    float targetEnergy;       // 0-1, target energy for this section
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
    
    // Phase 9: Genre-specific profile
    GenreProfile genreProfile;  // Genre characteristics and preferences
    
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

/**
 * Utility: Get human-readable name for track role
 */
const char* trackRoleName(TrackRole role);

/**
 * Phase 9: Pick genre profile based on image features and music parameters
 */
GenreProfile pickGenre(const ImageFeatures& features, const MusicParameters& params);

/**
 * Phase 9: Get section activity (which tracks are active) for a given genre and section
 */
SectionActivity getSectionActivity(const GenreProfile& genre, const SectionSpec& section, float moodScore);

/**
 * Phase 9: Get human-readable name for genre
 */
const char* genreName(Genre genre);
