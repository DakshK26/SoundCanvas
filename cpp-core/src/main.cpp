#include <iostream>
#include <stdexcept>

#include "ImageFeatures.hpp"
#include "AudioEngine.hpp"
#include "MusicMapping.hpp"

int main(int argc, char** argv) {
    if (argc != 3) {
        std::cerr << "Usage: soundcanvas_core <input_image> <output_wav>\n";
        return 1;
    }

    std::string inputImage = argv[1];
    std::string outputWav  = argv[2];

    try {
        std::cout << "Reading image: " << inputImage << std::endl;
        ImageFeatures features = extractImageFeatures(inputImage);

        std::cout << "Image features:\n"
                  << "  avgR=" << features.avgR
                  << "  avgG=" << features.avgG
                  << "  avgB=" << features.avgB
                  << "  brightness=" << features.brightness << std::endl;

        MusicParameters params = mapFeaturesToMusic(features);

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
