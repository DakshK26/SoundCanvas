#include "SongSpec.hpp"

#include <algorithm>
#include <cmath>

// MIDI note conversion: A4 = 440Hz = MIDI 69
int freqToMidiNote(float freq) {
  if (freq <= 0.0f) return 60;  // Default to C4
  float midi = 12.0f * std::log2(freq / 440.0f) + 69.0f;
  return static_cast<int>(std::round(midi));
}

SongSpec makeSongSpec(const ImageFeatures& f, const MusicParameters& m) {
  SongSpec spec;

  // ========== Global Parameters ==========

  // Tempo: quantize to musical values for better feel
  int tempoRounded = static_cast<int>(std::round(m.tempoBpm / 5.0f)) * 5;
  spec.tempoBpm = std::clamp(tempoRounded, 40, 180);  // Extended range for EDM

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
  }

  // ========== Phase 8: Song Structure (intro/build/drop/break/outro) ==========

  // Total bars based on energy: 16-32 bars for 45-90s tracks
  if (m.energy < 0.3f) {
    spec.totalBars = 16;  // ~30s at 80 BPM
  } else if (m.energy < 0.6f) {
    spec.totalBars = 24;  // ~45s at 80 BPM
  } else {
    spec.totalBars = 32;  // ~60s at 80 BPM
  }

  // Phase 8 Section Planning: EDM-style structure
  spec.sections.clear();

  if (spec.totalBars == 16) {
    // Short structure: intro(4) + build(4) + drop(4) + outro(4)
    spec.sections.push_back({"intro", 4, 0.2f});
    spec.sections.push_back({"build", 4, 0.5f});
    spec.sections.push_back({"drop", 4, 1.0f});
    spec.sections.push_back({"outro", 4, 0.2f});
  } else if (spec.totalBars == 24) {
    // Medium: intro(4) + build(6) + drop(8) + break(2) + outro(4)
    spec.sections.push_back({"intro", 4, 0.2f});
    spec.sections.push_back({"build", 6, 0.5f});
    spec.sections.push_back({"drop", 8, 1.0f});
    spec.sections.push_back({"break", 2, 0.4f});
    spec.sections.push_back({"outro", 4, 0.2f});
  } else {
    // Long: intro(4) + build(8) + drop(8) + break(4) + build2(4) + outro(4)
    spec.sections.push_back({"intro", 4, 0.2f});
    spec.sections.push_back({"build", 8, 0.5f});
    spec.sections.push_back({"drop", 8, 1.0f});
    spec.sections.push_back({"break", 4, 0.4f});
    spec.sections.push_back({"build2", 4, 0.6f});
    spec.sections.push_back({"outro", 4, 0.2f});
  }

  // ========== Phase 8: Track Roles & Assignments ==========

  spec.tracks.clear();

  // Track 1: Drums (General MIDI channel 9 = percussion)
  // Skip drums for very low energy or very ambient
  bool includeDrums = (m.energy > 0.25f) &&
                      (spec.groove != GrooveType::CHILL || m.energy > 0.5f);
  if (includeDrums) {
    spec.tracks.push_back({
        TrackRole::DRUMS,
        0.8f + m.energy * 0.15f,  // Base volume: louder with more energy
        m.energy,                 // Complexity: more fills/variations
        9,                        // MIDI channel 9 (drums in GM)
        0                         // Program ignored for drums
    });
  }

  // Track 2: Bass (always included unless very minimal)
  if (spec.moodScore > 0.2f || m.energy > 0.3f) {
    spec.tracks.push_back({
        TrackRole::BASS,
        0.8f,  // Strong bass presence
        m.energy * 0.6f,
        1,    // MIDI channel 1
        34    // Finger Bass (GM)
    });
  }

  // Track 3: Chords (harmonic foundation)
  // Pick program based on brightness and energy
  int chordProgram = (m.brightness > 0.5f) ? 4 : 89;  // Electric Piano or Pad
  spec.tracks.push_back({
      TrackRole::CHORDS,
      0.6f + spec.moodScore * 0.15f,
      0.5f + m.energy * 0.3f,
      2,  // MIDI channel 2
      chordProgram
  });

  // Track 4: Lead (melodic hooks - only if mood/energy high enough)
  if (spec.moodScore > 0.4f || m.energy > 0.5f) {
    spec.tracks.push_back({
        TrackRole::LEAD,
        0.7f,
        spec.moodScore * 0.7f + m.energy * 0.3f,
        3,   // MIDI channel 3
        81   // Lead 1 (square wave) - classic synth lead
    });
  }

  // Track 5: Pad (atmospheric layer)
  if (spec.moodScore > 0.3f || spec.groove == GrooveType::CHILL) {
    spec.tracks.push_back({
        TrackRole::PAD,
        0.4f + spec.moodScore * 0.2f,
        0.3f,  // Low complexity (sustained)
        4,     // MIDI channel 4
        91     // Pad 4 (choir) - warm atmospheric sound
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

const char* trackRoleName(TrackRole role) {
  switch (role) {
    case TrackRole::DRUMS:
      return "Drums";
    case TrackRole::BASS:
      return "Bass";
    case TrackRole::CHORDS:
      return "Chords";
    case TrackRole::LEAD:
      return "Lead";
    case TrackRole::PAD:
      return "Pad";
    case TrackRole::FX:
      return "FX";
    default:
      return "Unknown";
  }
}
