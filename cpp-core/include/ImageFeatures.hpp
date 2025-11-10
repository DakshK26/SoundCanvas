#pragma once
#include <string>

struct ImageFeatures {
    float avgR;
    float avgG;
    float avgB;
    float brightness;
};

ImageFeatures extractImageFeatures(const std::string& imagePath);
