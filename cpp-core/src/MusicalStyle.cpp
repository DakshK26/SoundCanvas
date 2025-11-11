#include "MusicalStyle.hpp"
#include <algorithm>
#include <cmath>

StyleParameters deriveStyle(const ImageFeatures& f, const MusicParameters& m) {
    StyleParameters style;

    // ========== Ambience Type ==========
    // Based on hue (color wheel), saturation, brightness, contrast
    
    // Blue tones (0.55-0.75 hue) + low contrast → Ocean
    if (f.hue >= 0.55f && f.hue <= 0.75f && f.contrast < 0.4f) {
        style.ambienceType = AmbienceType::OCEAN;
    }
    // Green tones (0.25-0.45 hue) + high saturation → Forest
    else if (f.hue >= 0.25f && f.hue <= 0.45f && f.saturation > 0.4f) {
        style.ambienceType = AmbienceType::FOREST;
    }
    // Dark (low brightness) + high contrast → City (night skyline, urban)
    else if (f.brightness < 0.4f && f.contrast > 0.5f) {
        style.ambienceType = AmbienceType::CITY;
    }
    // Very desaturated + low colorfulness → None/indoor (trash can, mundane)
    else if (f.saturation < 0.2f && f.colorfulness < 0.0015f) {
        style.ambienceType = AmbienceType::NONE;
    }
    // Default: Rain (neutral pleasant ambience for everything else)
    else {
        style.ambienceType = AmbienceType::RAIN;
    }

    // ========== Instrument Preset ==========
    // Based on pattern type, brightness, energy
    
    // Dark soft pad: low brightness, pad pattern
    if (m.patternType == 0 && m.brightness < 0.4f) {
        style.instrumentPreset = InstrumentPreset::SOFT_PAD;
    }
    // Plucks/harp: arpeggio pattern + high energy
    else if (m.patternType == 1 && m.energy > 0.5f) {
        style.instrumentPreset = InstrumentPreset::PLUCK;
    }
    // Bell-like: chord pattern + bright timbre
    else if (m.patternType == 2 && m.brightness > 0.5f) {
        style.instrumentPreset = InstrumentPreset::BELL;
    }
    // Default: Soft keys (piano-ish) for everything else
    else {
        style.instrumentPreset = InstrumentPreset::SOFT_KEYS;
    }

    // ========== Mood Score (Lushness) ==========
    // Combination of pleasant colors, lightness, smoothness
    // High mood = lush, cinematic (ocean sunset, forest)
    // Low mood = dry, minimal (trash can, gray concrete)
    
    // Pleasant colors: high saturation + colorfulness
    float pleasantColor = (f.saturation + std::min(f.colorfulness * 500.0f, 1.0f)) * 0.5f;
    
    // Lightness: brightness in mid-to-high range is more pleasant
    float lightness = f.brightness;
    
    // Roughness penalty: high contrast can be jarring
    float roughness = f.contrast;
    
    // Combine: weight pleasant colors heavily, add lightness, penalize roughness
    float baseMood = 0.6f * pleasantColor + 0.4f * lightness - 0.2f * roughness;
    
    // Clamp to [0, 1]
    style.moodScore = std::clamp(baseMood, 0.0f, 1.0f);

    return style;
}

const char* ambienceTypeName(AmbienceType type) {
    switch (type) {
        case AmbienceType::NONE:   return "None";
        case AmbienceType::OCEAN:  return "Ocean";
        case AmbienceType::RAIN:   return "Rain";
        case AmbienceType::FOREST: return "Forest";
        case AmbienceType::CITY:   return "City";
        default:                    return "Unknown";
    }
}

const char* instrumentPresetName(InstrumentPreset preset) {
    switch (preset) {
        case InstrumentPreset::SOFT_PAD:  return "Soft Pad";
        case InstrumentPreset::SOFT_KEYS: return "Soft Keys";
        case InstrumentPreset::PLUCK:     return "Pluck";
        case InstrumentPreset::BELL:      return "Bell";
        default:                           return "Unknown";
    }
}
