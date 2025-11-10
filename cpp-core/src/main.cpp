#include <iostream>
#include <stdexcept>
#include <string>
#include <cstdlib>

#include "ImageFeatures.hpp"
#include "AudioEngine.hpp"
#include "MusicMapping.hpp"
#include "ModelClient.hpp"

enum class Mode {
    Heuristic,
    Model
};

Mode parseMode(const std::string& s) {
    if (s == "heuristic") return Mode::Heuristic;
    if (s == "model") return Mode::Model;
    throw std::runtime_error("Unknown mode: " + s + " (expected 'heuristic' or 'model')");
}

int main(int argc, char** argv) {
    // Usage:
    //   soundcanvas_core <input_image> <output_wav>                          → heuristic mode (default)
    //   soundcanvas_core --mode=<heuristic|model> <input_image> <output_wav> → explicit mode
    
    if (argc < 3 || argc > 4) {
        std::cerr << "Usage:\n"
                  << "  soundcanvas_core <input_image> <output_wav>\n"
                  << "  soundcanvas_core --mode=<heuristic|model> <input_image> <output_wav>\n";
        return 1;
    }

    Mode mode = Mode::Heuristic;
    std::string inputImage;
    std::string outputWav;

    if (argc == 3) {
        // Default: heuristic mode (backward compatible)
        inputImage = argv[1];
        outputWav = argv[2];
    } else {
        // argc == 4: parse --mode=...
        std::string modeArg = argv[1];
        const std::string prefix = "--mode=";
        if (modeArg.rfind(prefix, 0) != 0) {
            std::cerr << "Invalid first argument: " << modeArg << std::endl;
            return 1;
        }
        mode = parseMode(modeArg.substr(prefix.size()));
        inputImage = argv[2];
        outputWav = argv[3];
    }

    try {
        std::cout << "Reading image: " << inputImage << std::endl;
        ImageFeatures features = extractImageFeatures(inputImage);

        std::cout << "Image features:\n"
                  << "  avgR=" << features.avgR
                  << "  avgG=" << features.avgG
                  << "  avgB=" << features.avgB
                  << "  brightness=" << features.brightness << std::endl;

        MusicParameters params;

        if (mode == Mode::Heuristic) {
            std::cout << "Using heuristic mapping.\n";
            params = mapFeaturesToMusicHeuristic(features);
        } else {
            std::cout << "Using model mapping via TF Serving.\n";

            // Get TF Serving URL from environment variable or use default
            const char* envUrl = std::getenv("SC_TF_SERVING_URL");
            std::string baseUrl = envUrl
                ? std::string(envUrl)
                : std::string("http://localhost:8501/v1/models/soundcanvas:predict");

            std::cout << "TF Serving URL: " << baseUrl << std::endl;

            ModelClient client(baseUrl);
            params = mapFeaturesToMusicModel(features, client);
        }

        std::cout << "Music parameters:\n"
                  << "  tempoBpm=" << params.tempoBpm
                  << "  baseFrequency=" << params.baseFrequency
                  << "  brightness=" << params.brightness
                  << "  volume=" << params.volume
                  << "  durationSeconds=" << params.durationSeconds
                  << std::endl;

        generateAmbientTrack(outputWav, params);
        std::cout << "Wrote audio to: " << outputWav << std::endl;

        return 0;
    } catch (const std::exception& ex) {
        std::cerr << "Error: " << ex.what() << std::endl;
        return 1;
    }
}