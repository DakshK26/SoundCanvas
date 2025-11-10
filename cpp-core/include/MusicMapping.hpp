#pragma once
#include "AudioEngine.hpp"
#include "ImageFeatures.hpp"

// Converts image features into music parameters using heuristic rules
MusicParameters mapFeaturesToMusic(const ImageFeatures& features);