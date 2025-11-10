#pragma once
#include <string>

struct MusicParameters {
  float tempoBpm;         // e.g. 40–100 BPM
  float baseFrequency;    // e.g. 110 Hz (A2) – 440 Hz (A4)
  float brightness;       // 0–1 -> affects waveform character
  float volume;           // 0–1 -> overall amplitude
  float durationSeconds;  // e.g. 8–12 seconds
};

// Generates a mono WAV file (16-bit PCM, 44.1kHz) with ambient audio
void generateAmbientTrack(const std::string& outputPath,
                          const MusicParameters& params);