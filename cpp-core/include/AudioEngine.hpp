#pragma once
#include <string>

struct MusicParameters {
  float tempoBpm;       // 40–90 BPM (slow ambient range)
  float baseFrequency;  // 100–400 Hz (bass to mid range)
  float energy;         // 0–1 (texture density/busyness)
  float brightness;     // 0–1 (filter cutoff, waveform choice)
  float reverb;         // 0–1 (dry to big hall)
  int scaleType;        // 0=major, 1=minor, 2=dorian, 3=lydian
  int patternType;      // 0=pad, 1=arp, 2=chords
};

// Phase 7: Extended style parameters for richer audio
struct StyleParameters {
  int ambienceType;      // 0=none, 1=ocean, 2=rain, 3=forest, 4=city
  int instrumentPreset;  // 0=soft_pad, 1=soft_keys, 2=pluck, 3=bell
  float moodScore;       // 0.0-1.0 (how lush/pleasant the soundscape should be)
};

// Forward declaration for Phase 7 style parameters
struct StyleParameters;

// Generates a mono WAV file (16-bit PCM, 44.1kHz) with ambient audio
// Phase 7: Now includes style parameters for richer output
void generateAmbientTrack(const std::string& outputPath,
                          const MusicParameters& params,
                          const StyleParameters& style);
