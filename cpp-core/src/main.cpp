#include <iostream>
#include <stdexcept>
#include <string>
#include <cstdlib>

#include "ImageFeatures.hpp"
#include "AudioEngine.hpp"
#include "MusicMapping.hpp"
#include "ModelClient.hpp"
#include "HttpServer.hpp"
#include "MusicalStyle.hpp"  // Phase 7: Extended style controls

enum class Mode {
    Heuristic,
    Model
};

Mode parseMode(const std::string& s) {
    if (s == "heuristic") return Mode::Heuristic;
    if (s == "model") return Mode::Model;
    throw std::runtime_error("Unknown mode: " + s + " (expected 'heuristic' or 'model')");
}

// Helper to get environment variable or return default
static std::string getEnvOrDefault(const char* key, const std::string& defaultValue) {
    const char* val = std::getenv(key);
    return val ? std::string(val) : defaultValue;
}

int main(int argc, char** argv) {
    // Check for server mode first
    if (argc >= 2 && std::string(argv[1]) == "--serve") {
        // HTTP server mode
        std::string defaultMode = getEnvOrDefault("SC_DEFAULT_MODE", "model");
        std::string outputDir = getEnvOrDefault("SC_OUTPUT_DIR", "../examples");
        
        int port = 8080;
        const char* portEnv = std::getenv("SC_HTTP_PORT");
        if (portEnv) {
            try {
                port = std::stoi(portEnv);
            } catch (...) {
                std::cerr << "Invalid SC_HTTP_PORT value, using default 8080" << std::endl;
            }
        }

        std::cout << "Starting HTTP server mode..." << std::endl;
        std::cout << "  Port: " << port << std::endl;
        std::cout << "  Default mode: " << defaultMode << std::endl;
        std::cout << "  Output directory: " << outputDir << std::endl;

        try {
            runHttpServer(port, defaultMode, outputDir);
            return 0;
        } catch (const std::exception& ex) {
            std::cerr << "Failed to start HTTP server: " << ex.what() << std::endl;
            return 1;
        }
    }

    // CLI mode (existing Phase 3 behavior)
    // Usage:
    //   soundcanvas_core <input_image> <output_wav>                          → heuristic mode (default)
    //   soundcanvas_core --mode=<heuristic|model> <input_image> <output_wav> → explicit mode
    
    if (argc < 3 || argc > 4) {
        std::cerr << "Usage:\n"
                  << "  soundcanvas_core --serve                                           → HTTP server mode\n"
                  << "  soundcanvas_core <input_image> <output_wav>                        → CLI heuristic mode\n"
                  << "  soundcanvas_core --mode=<heuristic|model> <input_image> <output_wav> → CLI with mode\n";
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

        std::cout << "Image features (8-dim):\n"
                  << "  avgR         = " << features.avgR << "\n"
                  << "  avgG         = " << features.avgG << "\n"
                  << "  avgB         = " << features.avgB << "\n"
                  << "  brightness   = " << features.brightness << "\n"
                  << "  hue          = " << features.hue << "\n"
                  << "  saturation   = " << features.saturation << "\n"
                  << "  colorfulness = " << features.colorfulness << "\n"
                  << "  contrast     = " << features.contrast << std::endl;

        MusicParameters params;

        if (mode == Mode::Heuristic) {
            std::cout << "Using heuristic mapping.\n";
            params = mapFeaturesToMusicHeuristic(features);
        } else {
            std::cout << "Using model mapping via TF Serving.\n";

            // Get TF Serving URL from environment variable or use default
            std::string baseUrl = getEnvOrDefault(
                "SC_TF_SERVING_URL",
                "http://localhost:8501/v1/models/soundcanvas:predict"
            );

            std::cout << "TF Serving URL: " << baseUrl << std::endl;

            ModelClient client(baseUrl);
            params = mapFeaturesToMusicModel(features, client);
        }

        // Map scale and pattern types to human-readable names
        const char* scaleNames[] = {"Major", "Minor", "Dorian", "Lydian"};
        const char* patternNames[] = {"Pad", "Arp", "Chords"};
        
        const char* scaleName = (params.scaleType >= 0 && params.scaleType <= 3) 
                                ? scaleNames[params.scaleType] 
                                : "Unknown";
        const char* patternName = (params.patternType >= 0 && params.patternType <= 2) 
                                  ? patternNames[params.patternType] 
                                  : "Unknown";

        std::cout << "Music parameters (7-dim):\n"
                  << "  tempoBpm      = " << params.tempoBpm << " BPM\n"
                  << "  baseFrequency = " << params.baseFrequency << " Hz\n"
                  << "  energy        = " << params.energy << "\n"
                  << "  brightness    = " << params.brightness << "\n"
                  << "  reverb        = " << params.reverb << "\n"
                  << "  scaleType     = " << params.scaleType << " (" << scaleName << ")\n"
                  << "  patternType   = " << params.patternType << " (" << patternName << ")"
                  << std::endl;

        // Phase 7: Derive extended style controls
        StyleParameters style = deriveStyle(features, params);
        
        std::cout << "Style parameters (Phase 7):\n"
                  << "  ambienceType      = " << ambienceTypeName(style.ambienceType) << "\n"
                  << "  instrumentPreset  = " << instrumentPresetName(style.instrumentPreset) << "\n"
                  << "  moodScore         = " << style.moodScore << " (lushness)"
                  << std::endl;

        generateAmbientTrack(outputWav, params, &style);
        std::cout << "Wrote audio to: " << outputWav << std::endl;

        return 0;
    } catch (const std::exception& ex) {
        std::cerr << "Error: " << ex.what() << std::endl;
        return 1;
    }
}