#pragma once

#include <string>
#include <vector>
#include <map>

/**
 * Phase 8: Genre-based EDM composition system
 * Enables structured tracks with build/drop/break sections
 */

enum class GenreType {
    EDM_CHILL = 0,    // Soft pads, melodic arps, chill vibes (100-115 BPM)
    EDM_DROP = 1,     // Side-chained synths, heavy kick, energy drops (125-135 BPM)
    RETROWAVE = 2,    // Analog bass, gated snare, 80s synth (90-110 BPM)
    CINEMATIC = 3     // Strings, percussion hits, dramatic build (70-90 BPM)
};

enum class SectionType {
    INTRO = 0,
    BUILD = 1,
    DROP = 2,
    BREAK = 3,
    OUTRO = 4
};

struct SectionTemplate {
    SectionType type;
    int bars;              // Number of bars in this section
    float energyLevel;     // 0-1: controls pattern complexity, instrument count
    bool hasDropTrigger;   // Should this section have a dramatic drop?
    
    std::string name() const;
};

struct InstrumentLayer {
    std::string role;      // "kick", "snare", "bass", "lead", "pad", "fx"
    int midiProgram;       // GM program number or synth patch ID
    float minEnergy;       // Only included if section energy >= this
    bool sidechainTarget;  // Should be ducked by kick (for EDM pump)
};

struct GenreTemplate {
    GenreType type;
    std::string name;
    
    // Tempo & feel
    int minTempo;
    int maxTempo;
    
    // Section structure plan
    std::vector<SectionTemplate> sectionPlan;
    
    // Instrument palette
    std::vector<InstrumentLayer> layers;
    
    // Drop trigger condition
    float dropEnergyThreshold;  // Only add drop section if image energy > this
    
    // Scale preferences
    std::vector<int> preferredScales;  // List of scaleType indices (0=Major, 1=Minor, etc.)
};

/**
 * Get the predefined template for a genre type
 */
const GenreTemplate& getGenreTemplate(GenreType type);

/**
 * Select genre based on image features (heuristic mapping)
 * - Blue/cool colors → EDM_Chill
 * - Red/warm + high energy → EDM_Drop
 * - High brightness + medium saturation → RetroWave
 * - Low colorfulness + contrast → Cinematic
 */
GenreType selectGenreFromImage(const struct ImageFeatures& features, float energy);

/**
 * Utility functions
 */
const char* genreTypeName(GenreType type);
const char* sectionTypeName(SectionType type);
