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

  // ========== Phase 9: Genre Selection ==========
  spec.genreProfile = pickGenre(f, m);

  // ========== Global Parameters ==========

  // Tempo: Clamp to genre range and quantize to musical values
  float clampedTempo = std::clamp(m.tempoBpm, spec.genreProfile.minTempo, 
                                   spec.genreProfile.maxTempo);
  int tempoRounded = static_cast<int>(std::round(clampedTempo / 5.0f)) * 5;
  spec.tempoBpm = tempoRounded;

  // Scale: Prefer genre-specific scales, but use model suggestion as hint
  if (!spec.genreProfile.preferredScaleTypes.empty()) {
    // If model scale is in preferred list, use it; otherwise use first preferred
    auto& preferred = spec.genreProfile.preferredScaleTypes;
    if (std::find(preferred.begin(), preferred.end(), m.scaleType) != preferred.end()) {
      spec.scaleType = m.scaleType;
    } else {
      spec.scaleType = preferred[0];
    }
  } else {
    spec.scaleType = m.scaleType;
  }

  // Root note
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

  // Phase 9: Genre-aware groove selection
  if (spec.genreProfile.genre == Genre::HOUSE || spec.genreProfile.genre == Genre::EDM_DROP) {
    spec.groove = GrooveType::DRIVING;  // Always driving for house/edm
  } else if (spec.genreProfile.genre == Genre::RAP || spec.genreProfile.genre == Genre::RNB) {
    spec.groove = GrooveType::STRAIGHT;  // Straight with swing for rap/rnb
  } else if (m.energy < 0.2f && spec.tempoBpm < 70) {
    spec.groove = GrooveType::CHILL;  // Sparse, ambient
  } else if (m.energy > 0.4f || spec.tempoBpm > 90) {
    spec.groove = GrooveType::DRIVING;  // Energetic, rhythmic
  } else {
    spec.groove = GrooveType::STRAIGHT;  // Standard 4/4
  }

  // ========== Phase 9: Genre-Aware Song Structure ==========

  // Total bars based on genre preferences and energy
  int genreMinBars = spec.genreProfile.minBars;
  int genreMaxBars = spec.genreProfile.maxBars;
  
  if (m.energy < 0.3f) {
    spec.totalBars = genreMinBars;
  } else if (m.energy < 0.6f) {
    spec.totalBars = (genreMinBars + genreMaxBars) / 2;
  } else {
    spec.totalBars = genreMaxBars;
  }

  // Genre-specific section templates
  spec.sections.clear();

  if (spec.genreProfile.genre == Genre::RAP) {
    // Rap structure: intro + verse + hook + verse/outro
    if (spec.totalBars == 16) {
      spec.sections.push_back({"intro", 4, 0.2f});
      spec.sections.push_back({"verse", 8, 0.5f});
      spec.sections.push_back({"hook", 4, 0.8f});
    } else {
      spec.sections.push_back({"intro", 4, 0.2f});
      spec.sections.push_back({"verse", 8, 0.5f});
      spec.sections.push_back({"hook", 8, 0.8f});
      spec.sections.push_back({"outro", 4, 0.3f});
    }
  } else if (spec.genreProfile.genre == Genre::RNB) {
    // R&B structure: intro + verse + pre-chorus + chorus + bridge? + outro
    if (spec.totalBars <= 24) {
      spec.sections.push_back({"intro", 4, 0.2f});
      spec.sections.push_back({"verse", 8, 0.5f});
      spec.sections.push_back({"pre-chorus", 4, 0.6f});
      spec.sections.push_back({"chorus", 8, 0.9f});
    } else {
      spec.sections.push_back({"intro", 4, 0.2f});
      spec.sections.push_back({"verse", 8, 0.5f});
      spec.sections.push_back({"pre-chorus", 4, 0.6f});
      spec.sections.push_back({"chorus", 8, 0.9f});
      spec.sections.push_back({"bridge", 4, 0.5f});
      spec.sections.push_back({"outro", 4, 0.3f});
    }
  } else if (spec.genreProfile.genre == Genre::HOUSE) {
    // House structure: intro + build + drop + break? + drop2? + outro
    if (spec.totalBars <= 24) {
      spec.sections.push_back({"intro", 4, 0.2f});
      spec.sections.push_back({"build", 8, 0.5f});
      spec.sections.push_back({"drop", 8, 1.0f});
      spec.sections.push_back({"outro", 4, 0.3f});
    } else {
      spec.sections.push_back({"intro", 4, 0.2f});
      spec.sections.push_back({"build", 8, 0.5f});
      spec.sections.push_back({"drop", 8, 1.0f});
      spec.sections.push_back({"break", 4, 0.4f});
      spec.sections.push_back({"drop2", 4, 1.0f});
      spec.sections.push_back({"outro", 4, 0.3f});
    }
  } else {
    // EDM_CHILL and EDM_DROP: Original EDM-style structure
    if (spec.totalBars == 16) {
      spec.sections.push_back({"intro", 4, 0.2f});
      spec.sections.push_back({"build", 4, 0.5f});
      spec.sections.push_back({"drop", 4, 1.0f});
      spec.sections.push_back({"outro", 4, 0.2f});
    } else if (spec.totalBars == 24) {
      spec.sections.push_back({"intro", 4, 0.2f});
      spec.sections.push_back({"build", 6, 0.5f});
      spec.sections.push_back({"drop", 8, 1.0f});
      spec.sections.push_back({"break", 2, 0.4f});
      spec.sections.push_back({"outro", 4, 0.2f});
    } else {
      spec.sections.push_back({"intro", 4, 0.2f});
      spec.sections.push_back({"build", 8, 0.5f});
      spec.sections.push_back({"drop", 8, 1.0f});
      spec.sections.push_back({"break", 4, 0.4f});
      spec.sections.push_back({"build2", 4, 0.6f});
      spec.sections.push_back({"outro", 4, 0.2f});
    }
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

// Phase 9: Genre utility functions
const char* genreName(Genre genre) {
  switch (genre) {
    case Genre::EDM_CHILL:
      return "EDM Chill";
    case Genre::EDM_DROP:
      return "EDM Drop";
    case Genre::HOUSE:
      return "House";
    case Genre::RAP:
      return "Rap";
    case Genre::RNB:
      return "R&B";
    default:
      return "Unknown";
  }
}

// Phase 9: Genre selection based on image features and music parameters
GenreProfile pickGenre(const ImageFeatures& f, const MusicParameters& m) {
  GenreProfile profile;
  
  // Analyze image characteristics
  float brightness = f.brightness;
  float saturation = f.saturation;
  float contrast = f.contrast;
  float warmth = f.warmth;
  
  // Decision logic for genre selection
  
  // House: Bright, saturated colors (party/neon vibes) OR tempo in house range
  if ((saturation > 0.6f && brightness > 0.5f) || 
      (m.tempoBpm >= 118 && m.tempoBpm <= 132)) {
    profile.genre = Genre::HOUSE;
    profile.name = "House";
    profile.minTempo = 118.0f;
    profile.maxTempo = 132.0f;
    profile.preferredScaleTypes = {0, 3};  // Major, Lydian (bright)
    profile.useSwing = false;
    profile.swingAmount = 0.0f;
    profile.heavySidechain = true;
    profile.drumPatternSets = {"house_basic", "house_groovy"};
    profile.chordProgressionSets = {"house_uplifting", "house_classic"};
    profile.bassPatternSets = {"house_groovy", "house_rolling"};
    profile.leadPatternSets = {"house_stabs", "house_melodic"};
    profile.minBars = 24;
    profile.maxBars = 32;
    profile.hasBigDrop = true;
    profile.hasBridge = false;
  }
  // Rap/Trap: High contrast + low saturation (urban/gritty) OR tempo in rap range
  else if ((contrast > 0.5f && saturation < 0.4f) || 
           (m.tempoBpm >= 70 && m.tempoBpm <= 100 && m.energy < 0.6f)) {
    profile.genre = Genre::RAP;
    profile.name = "Rap";
    profile.minTempo = 70.0f;
    profile.maxTempo = 100.0f;
    profile.preferredScaleTypes = {1, 2};  // Minor, Dorian (darker)
    profile.useSwing = true;
    profile.swingAmount = 0.15f;  // Medium swing
    profile.heavySidechain = false;
    profile.drumPatternSets = {"trap_808", "trap_syncopated"};
    profile.chordProgressionSets = {"trap_minimal", "trap_dark"};
    profile.bassPatternSets = {"trap_808", "trap_rolling"};
    profile.leadPatternSets = {"trap_sparse", "trap_melodic"};
    profile.minBars = 16;
    profile.maxBars = 24;
    profile.hasBigDrop = false;
    profile.hasBridge = false;
  }
  // R&B: High saturation + soft contrast + warm colors
  else if (saturation > 0.5f && contrast < 0.5f && warmth > 0.5f &&
           m.tempoBpm >= 70 && m.tempoBpm <= 95) {
    profile.genre = Genre::RNB;
    profile.name = "R&B";
    profile.minTempo = 70.0f;
    profile.maxTempo = 95.0f;
    profile.preferredScaleTypes = {0, 1, 2};  // Major, Minor, Dorian (versatile)
    profile.useSwing = true;
    profile.swingAmount = 0.2f;  // Stronger swing
    profile.heavySidechain = false;
    profile.drumPatternSets = {"rnb_soft", "rnb_groove"};
    profile.chordProgressionSets = {"rnb_jazzy", "rnb_extended"};
    profile.bassPatternSets = {"rnb_smooth", "rnb_walking"};
    profile.leadPatternSets = {"rnb_vocal", "rnb_melodic"};
    profile.minBars = 24;
    profile.maxBars = 32;
    profile.hasBigDrop = false;
    profile.hasBridge = true;
  }
  // EDM Drop: High energy
  else if (m.energy > 0.6f) {
    profile.genre = Genre::EDM_DROP;
    profile.name = "EDM Drop";
    profile.minTempo = 100.0f;
    profile.maxTempo = 140.0f;
    profile.preferredScaleTypes = {0, 1, 3};  // All scales
    profile.useSwing = false;
    profile.swingAmount = 0.0f;
    profile.heavySidechain = true;
    profile.drumPatternSets = {"edm_driving", "edm_buildup"};
    profile.chordProgressionSets = {"edm_progressive", "edm_classic"};
    profile.bassPatternSets = {"edm_wobble", "edm_driving"};
    profile.leadPatternSets = {"edm_lead", "edm_pluck"};
    profile.minBars = 24;
    profile.maxBars = 32;
    profile.hasBigDrop = true;
    profile.hasBridge = false;
  }
  // EDM Chill: Default/fallback
  else {
    profile.genre = Genre::EDM_CHILL;
    profile.name = "EDM Chill";
    profile.minTempo = 80.0f;
    profile.maxTempo = 110.0f;
    profile.preferredScaleTypes = {0, 2, 3};  // Major, Dorian, Lydian
    profile.useSwing = false;
    profile.swingAmount = 0.0f;
    profile.heavySidechain = false;
    profile.drumPatternSets = {"edm_chill", "edm_ambient"};
    profile.chordProgressionSets = {"edm_atmospheric", "edm_dreamy"};
    profile.bassPatternSets = {"edm_minimal", "edm_soft"};
    profile.leadPatternSets = {"edm_ambient", "edm_soft"};
    profile.minBars = 16;
    profile.maxBars = 24;
    profile.hasBigDrop = false;
    profile.hasBridge = false;
  }
  
  return profile;
}

// Phase 9: Determine which tracks are active in each section based on genre
SectionActivity getSectionActivity(const GenreProfile& genre, 
                                    const SectionSpec& section, 
                                    float moodScore) {
  SectionActivity activity = {false, false, false, false, false};
  
  std::string sectionName = section.name;
  float energy = section.targetEnergy;
  
  // Genre-specific section activity patterns
  if (genre.genre == Genre::HOUSE) {
    // House: Gradual build, full arrangement in drop
    if (sectionName == "intro") {
      activity.drums = false;
      activity.bass = true;
      activity.chords = true;
      activity.lead = false;
      activity.pad = true;
    } else if (sectionName == "build" || sectionName == "build2") {
      activity.drums = true;
      activity.bass = true;
      activity.chords = true;
      activity.lead = (energy > 0.4f);
      activity.pad = true;
    } else if (sectionName == "drop") {
      activity.drums = true;
      activity.bass = true;
      activity.chords = true;
      activity.lead = true;
      activity.pad = true;
    } else if (sectionName == "break") {
      activity.drums = false;
      activity.bass = true;
      activity.chords = true;
      activity.lead = false;
      activity.pad = true;
    } else {  // outro
      activity.drums = true;
      activity.bass = true;
      activity.chords = true;
      activity.lead = false;
      activity.pad = true;
    }
  } else if (genre.genre == Genre::RAP) {
    // Rap: Focus on drums + bass, sparse melodic elements
    if (sectionName == "intro") {
      activity.drums = false;
      activity.bass = false;
      activity.chords = (moodScore > 0.3f);
      activity.lead = false;
      activity.pad = true;
    } else if (sectionName == "build" || sectionName == "build2") {
      activity.drums = true;
      activity.bass = true;
      activity.chords = (moodScore > 0.4f);
      activity.lead = false;
      activity.pad = (moodScore > 0.5f);
    } else if (sectionName == "drop") {
      // In rap, "drop" is more like a chorus/hook
      activity.drums = true;
      activity.bass = true;
      activity.chords = true;
      activity.lead = true;
      activity.pad = (moodScore > 0.4f);
    } else if (sectionName == "break") {
      activity.drums = false;
      activity.bass = true;
      activity.chords = true;
      activity.lead = false;
      activity.pad = true;
    } else {  // outro
      activity.drums = true;
      activity.bass = true;
      activity.chords = (moodScore > 0.3f);
      activity.lead = false;
      activity.pad = false;
    }
  } else if (genre.genre == Genre::RNB) {
    // R&B: Smooth, all elements usually present but with dynamics
    if (sectionName == "intro") {
      activity.drums = false;
      activity.bass = false;
      activity.chords = true;
      activity.lead = false;
      activity.pad = true;
    } else if (sectionName == "build" || sectionName == "build2") {
      // Build is like a verse in R&B
      activity.drums = true;
      activity.bass = true;
      activity.chords = true;
      activity.lead = (energy > 0.4f);
      activity.pad = true;
    } else if (sectionName == "drop") {
      // Drop is like a chorus - fuller arrangement
      activity.drums = true;
      activity.bass = true;
      activity.chords = true;
      activity.lead = true;
      activity.pad = true;
    } else if (sectionName == "break") {
      // Bridge section
      activity.drums = true;
      activity.bass = true;
      activity.chords = true;
      activity.lead = false;
      activity.pad = true;
    } else {  // outro
      activity.drums = false;
      activity.bass = true;
      activity.chords = true;
      activity.lead = false;
      activity.pad = true;
    }
  } else {
    // EDM_CHILL and EDM_DROP: Original behavior (energy-based)
    activity.drums = (energy > 0.25f);
    activity.bass = (energy > 0.2f || moodScore > 0.3f);
    activity.chords = true;
    activity.lead = (energy > 0.4f || moodScore > 0.5f);
    activity.pad = (energy < 0.7f && moodScore > 0.3f);
  }
  
  return activity;
}
