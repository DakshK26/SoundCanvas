#include "MusicMapping.hpp"

#include <algorithm>

static float clamp01(float x) {
  if (x < 0.0f) return 0.0f;
  if (x > 1.0f) return 1.0f;
  return x;
}

MusicParameters mapFeaturesToMusic(const ImageFeatures& f) {
  float brightness = clamp01(f.brightness);

  // Tempo: darker images -> slower, brighter images -> faster
  float tempo = 40.0f + brightness * 60.0f;  // 40–100 BPM

  // Base frequency: use blue channel as a rough proxy for pitch
  float baseFreq = 110.0f + f.avgB * 220.0f;  // 110–330 Hz

  // Volume: keep constant for now
  float volume = 0.5f;

  // Duration: darker images get longer tracks
  float duration = 8.0f + (1.0f - brightness) * 4.0f;  // 8–12 seconds

  MusicParameters params;
  params.tempoBpm = tempo;
  params.baseFrequency = baseFreq;
  params.brightness = brightness;
  params.volume = volume;
  params.durationSeconds = duration;

  return params;
}