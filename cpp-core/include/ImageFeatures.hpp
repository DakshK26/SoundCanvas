#pragma once
#include <string>

struct ImageFeatures {
    float avgR;         // [0] 0–1 (average red channel)
    float avgG;         // [1] 0–1 (average green channel)
    float avgB;         // [2] 0–1 (average blue channel)
    float brightness;   // [3] 0–1 (mean luminance)
    float hue;          // [4] 0–1 (HSV hue, normalized)
    float saturation;   // [5] 0–1 (HSV saturation)
    float colorfulness; // [6] 0–1 (Hasler & Süsstrunk metric)
    float contrast;     // [7] 0–1 (grayscale std dev, normalized)
};

ImageFeatures extractImageFeatures(const std::string& imagePath);
