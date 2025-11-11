#pragma once

#include "ImageFeatures.hpp"
#include "AudioEngine.hpp"
#include "SongSpec.hpp"  // Use enums from SongSpec.hpp

struct StyleParameters {
    AmbienceType ambienceType;
    InstrumentPreset instrumentPreset;
    float moodScore;  // 0-1: how lush/pleasant the soundscape should be
};

/**
 * Derive extended style controls from image features and music parameters.
 * Uses heuristics based on:
 *   - hue (color wheel position) → ambience type
 *   - saturation, colorfulness → mood/lushness
 *   - pattern type, brightness, energy → instrument choice
 */
StyleParameters deriveStyle(const ImageFeatures& features, const MusicParameters& params);
