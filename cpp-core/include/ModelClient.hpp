#pragma once

#include <string>
#include "ImageFeatures.hpp"
#include "AudioEngine.hpp"  // for MusicParameters

// Thin client around TensorFlow Serving's REST API.
class ModelClient {
public:
    // baseUrl should be the full predict URL, e.g.:
    // "http://localhost:8501/v1/models/soundcanvas:predict"
    explicit ModelClient(const std::string& baseUrl);

    // Send features to TF Serving and get back music parameters.
    // Throws std::runtime_error on failure.
    MusicParameters predict(const ImageFeatures& features) const;

private:
    std::string baseUrl_;
};
