#pragma once

#include "ImageFeatures.hpp"
#include "AudioEngine.hpp"

/**
 * Phase 7: Extended style controls derived from image features + music parameters.
 * These add ambience, instrument choice, and "lushness" without changing the ML model.
 */

enum class AmbienceType {
    NONE = 0,       // Dry/indoor, subtle room tone
    OCEAN = 1,      // Wave sounds, beach atmosphere
    RAIN = 2,       // Neutral pleasant rainfall
    FOREST = 3,     // Birds, insects, nature sounds
    CITY = 4        // Distant traffic, urban hum
};

enum class InstrumentPreset {
    SOFT_PAD = 0,   // Sustained drone (existing pad)
    SOFT_KEYS = 1,  // Piano/keys-like with medium decay
    PLUCK = 2,      // Harp/string plucks with quick decay
    BELL = 3        // Bell/mallet with bright harmonics
};

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

/**
 * Convert enum to human-readable string for logging.
 */
const char* ambienceTypeName(AmbienceType type);
const char* instrumentPresetName(InstrumentPreset preset);
