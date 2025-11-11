#include "MusicMapping.hpp"

#include <algorithm>
#include <cmath>
#include <iostream>
#include <stdexcept>

// Helper functions
static float clamp01(float x) { return std::max(0.0f, std::min(1.0f, x)); }

static float clamp(float x, float lo, float hi) {
  return std::max(lo, std::min(hi, x));
}

// --- Heuristic mapping (Phase 5.5 logic - ported from Python) ---
MusicParameters mapFeaturesToMusicHeuristic(const ImageFeatures& f) {
  // Destructure for readability
  float avgR = f.avgR;
  float avgG = f.avgG;
  float avgB = f.avgB;
  float brightness = clamp01(f.brightness);
  float hue = clamp01(f.hue);
  float saturation = clamp01(f.saturation);
  float colorfulness = clamp01(f.colorfulness);
  float contrast = clamp01(f.contrast);

  MusicParameters p{};

  // === TEMPO: darker images → slower, brighter → faster ===
  // Range: 40-90 BPM (ambient/downtempo)
  float tempo = 40.0f + brightness * 50.0f;  // Dark: ~40, Bright: ~90

  // Add subtle variation from contrast (high contrast → slight tempo increase)
  tempo += contrast * 10.0f;
  p.tempoBpm = clamp(tempo, 40.0f, 90.0f);

  // === BASE FREQUENCY: influenced by color temperature ===
  // Blue-ish (cool) → lower frequencies
  // Red-ish (warm) → higher frequencies
  // Range: 100-400 Hz

  // Compute "warmth" from R vs B balance
  float warmth = (avgR - avgB + 1.0f) / 2.0f;  // Maps to [0, 1] approx
  warmth = clamp01(warmth);

  p.baseFrequency = 100.0f + warmth * 300.0f;  // Cool: ~100Hz, Warm: ~400Hz

  // === ENERGY: saturation + colorfulness → busier textures ===
  // Range: 0.0-1.0
  // Low saturation → simple drones
  // High saturation → richer, more active textures
  p.energy = clamp01(saturation * 0.6f + colorfulness * 0.4f);

  // === BRIGHTNESS (timbre): matches visual brightness ===
  // Range: 0.0-1.0
  // Controls filter cutoff / waveform selection
  p.brightness = brightness;

  // === REVERB: darker/moodier images → more reverb (distant feel) ===
  // Range: 0.0-1.0
  // Dark images → spacious, ethereal
  // Bright images → more present, less reverb
  float reverb = (1.0f - brightness) * 0.7f + (1.0f - saturation) * 0.3f;
  p.reverb = clamp01(reverb);

  // === SCALE TYPE: hue → harmonic flavor ===
  // 0 = major (warm, uplifting)
  // 1 = minor (cool, introspective)
  // 2 = dorian (balanced, jazzy)
  // 3 = lydian (bright, dreamy)

  // Hue ranges (approximate):
  // Red/Orange: 0.0-0.15 → major/mixolydian
  // Yellow/Green: 0.15-0.45 → lydian
  // Cyan/Blue: 0.45-0.65 → minor
  // Purple/Magenta: 0.65-1.0 → dorian

  if (hue < 0.15f) {
    p.scaleType = 0;  // major (warm reds/oranges)
  } else if (hue < 0.45f) {
    p.scaleType = 3;  // lydian (yellow/green, bright and open)
  } else if (hue < 0.65f) {
    p.scaleType = 1;  // minor (blue, cool and introspective)
  } else {
    p.scaleType = 2;  // dorian (purple/magenta, balanced)
  }

  // === PATTERN TYPE: energy level determines texture complexity ===
  // 0 = pad (sustained drone, simple)
  // 1 = arp (gentle arpeggios, medium)
  // 2 = chords (block chords, more harmonic movement)

  if (p.energy < 0.35f) {
    p.patternType = 0;  // Low energy → simple pad
  } else if (p.energy < 0.70f) {
    p.patternType = 1;  // Medium energy → gentle arpeggios
  } else {
    p.patternType = 2;  // High energy → chord progression
  }

  return p;
}

// --- Model-based mapping with fallback ---
MusicParameters mapFeaturesToMusicModel(const ImageFeatures& features,
                                        const ModelClient& client) {
  try {
    // Try to get prediction from TF Serving
    MusicParameters fromModel = client.predict(features);

    // Apply safety clamping to ensure values are in valid ranges
    // (model should already output good values, but this is a safety net)

    // Clamp continuous fields
    fromModel.tempoBpm = clamp(fromModel.tempoBpm, 40.0f, 90.0f);
    fromModel.baseFrequency = clamp(fromModel.baseFrequency, 100.0f, 400.0f);
    fromModel.energy = clamp01(fromModel.energy);
    fromModel.brightness = clamp01(fromModel.brightness);
    fromModel.reverb = clamp01(fromModel.reverb);

    // Clamp discrete fields
    fromModel.scaleType = std::clamp(fromModel.scaleType, 0, 3);
    fromModel.patternType = std::clamp(fromModel.patternType, 0, 2);

    std::cout << "[INFO] Model prediction successful.\n";
    return fromModel;
  } catch (const std::exception& ex) {
    // If TF Serving is down or returns error, fall back to heuristic
    std::cerr
        << "[WARN] Model prediction failed, falling back to heuristic. Reason: "
        << ex.what() << std::endl;
    return mapFeaturesToMusicHeuristic(features);
  }
}

// --- Phase 7: Derive extended style parameters from image features ---
StyleParameters deriveStyle(const ImageFeatures& f, const MusicParameters& m) {
  StyleParameters s{};

  // === AMBIENCE TYPE ===
  // Derive from hue, saturation, colorfulness, brightness, contrast

  // Ocean-like: dominant blue hues (0.55-0.75), low contrast
  if (f.hue > 0.55f && f.hue < 0.75f && f.contrast < 0.4f) {
    s.ambienceType = 1;  // Ocean
  }
  // Forest-like: dominant green hues (0.25-0.45), high saturation
  else if (f.hue > 0.25f && f.hue < 0.45f && f.saturation > 0.4f) {
    s.ambienceType = 3;  // Forest
  }
  // City-like: dark with high contrast (night skyline)
  else if (f.brightness < 0.4f && f.contrast > 0.5f) {
    s.ambienceType = 4;  // City
  }
  // Mundane/Indoor: very low saturation & colorfulness
  else if (f.saturation < 0.2f && f.colorfulness < 0.15f) {
    s.ambienceType = 0;  // None / subtle room tone
  }
  // Default: rain (neutral pleasant ambience)
  else {
    s.ambienceType = 2;  // Rain
  }

  // === INSTRUMENT PRESET ===
  // Based on pattern type, brightness, and energy

  if (m.patternType == 0 && m.brightness < 0.4f) {
    // Dark pad pattern → soft pad
    s.instrumentPreset = 0;  // SOFT_PAD
  } else if (m.patternType == 1 && m.energy > 0.5f) {
    // Energetic arp → plucky/harp sounds
    s.instrumentPreset = 2;  // PLUCK
  } else if (m.patternType == 2 && m.brightness > 0.5f) {
    // Bright chords → bell-like tones
    s.instrumentPreset = 3;  // BELL
  } else {
    // Default: soft piano-ish
    s.instrumentPreset = 1;  // SOFT_KEYS
  }

  // === MOOD SCORE ===
  // How lush and pleasant the soundscape should be
  // Higher for pleasant images (good saturation, colorfulness, balanced
  // brightness) Lower for mundane/ugly images (low saturation, dull colors)

  float pleasantColor = (f.saturation + f.colorfulness) * 0.5f;
  float lightness = f.brightness;
  float roughness = f.contrast;

  // Combine factors:
  // - Pleasant colors contribute positively
  // - Good lightness contributes positively
  // - Too much contrast (harshness) detracts
  float baseMood = 0.6f * pleasantColor + 0.4f * lightness - 0.3f * roughness;

  s.moodScore = clamp01(baseMood);

  return s;
}