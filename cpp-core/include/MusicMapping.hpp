#pragma once

#include "AudioEngine.hpp"
#include "ImageFeatures.hpp"
#include "ModelClient.hpp"

// Heuristic mapping (Phase 1 logic) - fallback when model unavailable
MusicParameters mapFeaturesToMusicHeuristic(const ImageFeatures& features);

// Model-based mapping - calls TF Serving, falls back to heuristic on error
MusicParameters mapFeaturesToMusicModel(const ImageFeatures& features,
                                        const ModelClient& client);