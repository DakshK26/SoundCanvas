#pragma once

#include "GenreTemplate.hpp"
#include "SongSpec.hpp"
#include "ImageFeatures.hpp"
#include "AudioEngine.hpp"

/**
 * Phase 8: Section Planning Engine
 * Generates song structure (intro/build/drop/break/outro) based on genre templates
 */

struct PlannedSection {
    SectionType type;
    int startBar;
    int bars;
    float energy;
    bool hasDrop;
    
    // Automation curves for this section
    bool filterSweep;      // Ramp up filter cutoff before drop
    bool volumeBuild;      // Gradual volume increase
    float dropIntensity;   // 0-1: how dramatic the drop should be
};

struct SongPlan {
    GenreType genre;
    int totalBars;
    int tempoBpm;
    int scaleType;
    int rootNote;
    
    std::vector<PlannedSection> sections;
    std::vector<std::string> activeInstruments;  // List of instrument roles to render
};

/**
 * Generate a complete song plan from image features and genre template
 */
SongPlan planSong(const ImageFeatures& features, 
                  const MusicParameters& params,
                  const GenreTemplate& genreTemplate);

/**
 * Convert SongPlan to SongSpec (for backward compatibility with existing renderer)
 */
SongSpec songPlanToSpec(const SongPlan& plan);
