#include "ModelClient.hpp"
#include "ImageFeatures.hpp"
#include <iostream>

int main() {
    std::string url = std::getenv("SC_TF_SERVING_URL")
        ? std::getenv("SC_TF_SERVING_URL")
        : "http://localhost:8501/v1/models/soundcanvas:predict";

    ModelClient client(url);

    ImageFeatures f;
    f.avgR = 0.8f;
    f.avgG = 0.6f;
    f.avgB = 0.2f;
    f.brightness = (f.avgR + f.avgG + f.avgB) / 3.0f;

    try {
        MusicParameters p = client.predict(f);
        std::cout << "Prediction: tempo=" << p.tempoBpm
                  << " baseFreq=" << p.baseFrequency
                  << " brightness=" << p.brightness
                  << " volume=" << p.volume
                  << " duration=" << p.durationSeconds
                  << std::endl;
    } catch (const std::exception& e) {
        std::cerr << "ModelClient test failed: " << e.what() << std::endl;
        return 1;
    }

    return 0;
}
