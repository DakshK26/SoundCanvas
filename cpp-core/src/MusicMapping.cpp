#include "MusicMapping.hpp"
#include <algorithm>
#include <iostream>
#include <stdexcept>

// Helper function
static float clamp01(float x) {
    if (x < 0.0f) return 0.0f;
    if (x > 1.0f) return 1.0f;
    return x;
}

// --- Heuristic mapping (Phase 1 logic - unchanged) ---
MusicParameters mapFeaturesToMusicHeuristic(const ImageFeatures& f) {
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

// --- Model-based mapping with fallback ---
MusicParameters mapFeaturesToMusicModel(const ImageFeatures& features, const ModelClient& client) {
    try {
        // Try to get prediction from TF Serving
        MusicParameters fromModel = client.predict(features);
        std::cout << "[INFO] Model prediction successful.\n";
        return fromModel;
    } catch (const std::exception& ex) {
        // If TF Serving is down or returns error, fall back to heuristic
        std::cerr << "[WARN] Model prediction failed, falling back to heuristic. Reason: "
                  << ex.what() << std::endl;
        return mapFeaturesToMusicHeuristic(features);
    }
}