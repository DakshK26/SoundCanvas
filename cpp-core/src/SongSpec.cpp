#include "SongSpec.hpp"

#include <algorithm>
#include <cmath>

// MIDI note conversion: A4 = 440Hz = MIDI 69
int freqToMidiNote(float freq) {
  if (freq <= 0.0f) return 60;  // Default to C4
  float midi = 12.0f * std::log2(freq / 440.0f) + 69.0f;
  return static_cast<int>(std::round(midi));
}

// General MIDI program numbers for different presets
static int getProgramNumber(InstrumentPreset preset, int scaleType) {
  switch (preset) {
    case InstrumentPreset::SOFT_PAD:
      return 89;  // Pad 2 (warm)
    case InstrumentPreset::KEYS:
      // Major/Lydian = bright piano, Minor/Dorian = electric piano
      return (scaleType == 0 || scaleType == 3) ? 0
                                                : 4;  // Acoustic/Electric Piano
    case InstrumentPreset::PLUCK:
      return 46;  // Orchestral Harp
    case InstrumentPreset::BELL:
      return 11;  // Vibraphone
    default:
      return 0;
  }
}

SongSpec makeSongSpec(const ImageFeatures& f, const MusicParameters& m) {
  SongSpec spec;

  // ========== Global Parameters ==========

  // Tempo: quantize to musical values for better feel
  int tempoRounded = static_cast<int>(std::round(m.tempoBpm / 5.0f)) * 5;
  spec.tempoBpm = std::clamp(tempoRounded, 40, 140);

  // Scale & root note
  spec.scaleType = m.scaleType;
  spec.rootMidiNote = freqToMidiNote(m.baseFrequency);

  // Ensure root is in reasonable range (C2 to C5)
  while (spec.rootMidiNote < 36) spec.rootMidiNote += 12;
  while (spec.rootMidiNote > 72) spec.rootMidiNote -= 12;

  // ========== Mood & Ambience ==========

  // Mood score: combination of pleasant colors + lightness - roughness
  float pleasantColor =
      (f.saturation + std::min(f.colorfulness * 500.0f, 1.0f)) * 0.5f;
  float lightness = f.brightness;
  float roughness = f.contrast;
  float baseMood = 0.6f * pleasantColor + 0.4f * lightness - 0.2f * roughness;
  spec.moodScore = std::clamp(baseMood, 0.0f, 1.0f);

  // Ambience type from hue + visual characteristics
  if (f.hue >= 0.55f && f.hue <= 0.75f && f.contrast < 0.4f) {
    spec.ambience = AmbienceType::OCEAN;
  } else if (f.hue >= 0.25f && f.hue <= 0.45f && f.saturation > 0.4f) {
    spec.ambience = AmbienceType::FOREST;
  } else if (f.brightness < 0.4f && f.contrast > 0.5f) {
    spec.ambience = AmbienceType::CITY;
  } else if (f.saturation < 0.2f && f.colorfulness < 0.0015f) {
    spec.ambience = AmbienceType::NONE;
  } else {
    spec.ambience = AmbienceType::RAIN;
  }

  // ========== Song Structure & Length ==========

  // Total bars based on energy and mood
  // Low energy/mood = shorter (16 bars = ~30s at 80bpm)
  // High energy/mood = longer (32-48 bars = 60-90s)
  if (m.energy < 0.3f && spec.moodScore < 0.4f) {
    spec.totalBars = 16;
  } else if (m.energy < 0.6f || spec.moodScore < 0.6f) {
    spec.totalBars = 24;
  } else {
    spec.totalBars = 32;
  }

  // Sections: intro, A, optional B, outro
  spec.sections.clear();

  if (spec.totalBars == 16) {
    // Simple: intro(4) + A(8) + outro(4)
    spec.sections.push_back({"intro", 4, m.energy * 0.5f});
    spec.sections.push_back({"A", 8, m.energy});
    spec.sections.push_back({"outro", 4, m.energy * 0.6f});
  } else if (spec.totalBars == 24) {
    // Medium: intro(4) + A(8) + B(8) + outro(4)
    spec.sections.push_back({"intro", 4, m.energy * 0.5f});
    spec.sections.push_back({"A", 8, m.energy});
    spec.sections.push_back({"B", 8, m.energy * 0.9f});
    spec.sections.push_back({"outro", 4, m.energy * 0.6f});
  } else {
    // Long: intro(4) + A(12) + B(12) + outro(4)
    spec.sections.push_back({"intro", 4, m.energy * 0.5f});
    spec.sections.push_back({"A", 12, m.energy});
    spec.sections.push_back({"B", 12, m.energy * 0.95f});
    spec.sections.push_back({"outro", 4, m.energy * 0.6f});
  }

  // ========== Groove Type ==========

  // Determine rhythm style from tempo + energy + pattern
  // Made more accessible to get variety:
  // - DRIVING: Medium-high energy (>0.4) OR fast tempo (>90)
  // - CHILL: Very low energy (<0.2) AND slow
  // - STRAIGHT: Everything else
  if (m.energy < 0.2f && spec.tempoBpm < 70) {
    spec.groove = GrooveType::CHILL;  // Sparse, ambient
  } else if (m.energy > 0.4f || spec.tempoBpm > 90) {
    spec.groove = GrooveType::DRIVING;  // Energetic, rhythmic
  } else {
    spec.groove = GrooveType::STRAIGHT;  // Standard 4/4
  }  // ========== Track Assignments ==========

  spec.tracks.clear();

  // 1. Drums (if appropriate)
  // Skip drums for very low energy or very ambient (chill pad-only tracks)
  bool includeDrums = (m.energy > 0.25f) &&
                      (spec.groove != GrooveType::CHILL || m.energy > 0.5f);
  if (includeDrums) {
    spec.tracks.push_back({
        "drums",
        InstrumentPreset::KEYS,  // Not used for drums (channel 10)
        0,                       // Drums use channel 10, program change ignored
        0.6f + m.energy * 0.3f,  // Volume: louder with more energy
        m.energy  // Complexity: more fills/variations with energy
    });
  }

  // 2. Bass (always included unless very minimal)
  if (spec.moodScore > 0.2f || m.energy > 0.3f) {
    spec.tracks.push_back({
        "bass", InstrumentPreset::KEYS,
        32 + (m.scaleType % 4),  // Acoustic Bass (32-35 variants)
        0.7f,
        m.energy * 0.6f  // Less complex than melody
    });
  }

  // 3. Chords (main harmonic foundation)
  // Pick instrument based on scale type and brightness
  InstrumentPreset chordPreset;
  if (m.scaleType == 0 || m.scaleType == 3) {
    // Major/Lydian: brighter sounds
    chordPreset = (m.brightness > 0.5f) ? InstrumentPreset::KEYS
                                        : InstrumentPreset::PLUCK;
  } else {
    // Minor/Dorian: warmer sounds
    chordPreset =
        (m.brightness > 0.5f) ? InstrumentPreset::BELL : InstrumentPreset::KEYS;
  }

  spec.tracks.push_back({"chords", chordPreset,
                         getProgramNumber(chordPreset, m.scaleType),
                         0.5f + spec.moodScore * 0.2f, 0.5f + m.energy * 0.3f});

  // 4. Melody (only if mood is high enough - lush scenes deserve melody)
  if (spec.moodScore > 0.4f) {
    InstrumentPreset melodyPreset;
    if (spec.moodScore > 0.7f) {
      // Very pleasant: use bell-like sounds
      melodyPreset = InstrumentPreset::BELL;
    } else if (m.brightness > 0.6f) {
      // Bright: plucks
      melodyPreset = InstrumentPreset::PLUCK;
    } else {
      // Default: keys
      melodyPreset = InstrumentPreset::KEYS;
    }

    spec.tracks.push_back({
        "melody", melodyPreset, getProgramNumber(melodyPreset, m.scaleType),
        0.4f + spec.moodScore * 0.3f,
        spec.moodScore  // Melody complexity tracks mood
    });
  }

  // 5. Pad (sustained background layer)
  // Include for most tracks unless very minimal
  if (spec.moodScore > 0.3f || m.patternType == 0) {
    spec.tracks.push_back({
        "pad", InstrumentPreset::SOFT_PAD,
        getProgramNumber(InstrumentPreset::SOFT_PAD, m.scaleType),
        0.3f + spec.moodScore * 0.2f,  // Subtle volume
        0.3f                           // Low complexity (long sustained notes)
    });
  }

  return spec;
}

// Utility functions
const char* ambienceTypeName(AmbienceType type) {
  switch (type) {
    case AmbienceType::NONE:
      return "None";
    case AmbienceType::OCEAN:
      return "Ocean";
    case AmbienceType::RAIN:
      return "Rain";
    case AmbienceType::FOREST:
      return "Forest";
    case AmbienceType::CITY:
      return "City";
    default:
      return "Unknown";
  }
}

const char* instrumentPresetName(InstrumentPreset preset) {
  switch (preset) {
    case InstrumentPreset::SOFT_PAD:
      return "Soft Pad";
    case InstrumentPreset::KEYS:
      return "Keys";
    case InstrumentPreset::PLUCK:
      return "Pluck";
    case InstrumentPreset::BELL:
      return "Bell";
    default:
      return "Unknown";
  }
}

const char* grooveTypeName(GrooveType type) {
  switch (type) {
    case GrooveType::STRAIGHT:
      return "Straight";
    case GrooveType::CHILL:
      return "Chill";
    case GrooveType::DRIVING:
      return "Driving";
    default:
      return "Unknown";
  }
}
