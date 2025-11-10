#define STB_IMAGE_IMPLEMENTATION
#include "stb_image.h"

#include "ImageFeatures.hpp"
#include <stdexcept>
#include <cmath>
#include <vector>
#include <algorithm>

// Helper: Convert RGB [0,1] to HSV [H: 0-360, S: 0-1, V: 0-1]
static void rgbToHsv(float r, float g, float b, float& h, float& s, float& v) {
    float cmax = std::max({r, g, b});
    float cmin = std::min({r, g, b});
    float delta = cmax - cmin;

    // Value
    v = cmax;

    // Saturation
    if (cmax == 0.0f) {
        s = 0.0f;
    } else {
        s = delta / cmax;
    }

    // Hue
    if (delta == 0.0f) {
        h = 0.0f;  // undefined, but we'll use 0
    } else if (cmax == r) {
        h = 60.0f * fmodf(((g - b) / delta), 6.0f);
    } else if (cmax == g) {
        h = 60.0f * (((b - r) / delta) + 2.0f);
    } else {
        h = 60.0f * (((r - g) / delta) + 4.0f);
    }

    if (h < 0.0f) h += 360.0f;
}

ImageFeatures extractImageFeatures(const std::string& imagePath) {
    int width, height, channels;
    unsigned char* data = stbi_load(imagePath.c_str(), &width, &height, &channels, 3);
    if (!data) {
        throw std::runtime_error("Failed to load image: " + imagePath);
    }

    const int numPixels = width * height;
    
    // Accumulate RGB for averages
    long long sumR = 0, sumG = 0, sumB = 0;
    
    // Accumulate HSV for averages
    double sumHue = 0.0, sumSat = 0.0;
    
    // Accumulate for colorfulness metric
    double sumRG = 0.0, sumYB = 0.0;
    double sumRG_sq = 0.0, sumYB_sq = 0.0;
    
    // Accumulate for contrast
    std::vector<float> grayValues;
    grayValues.reserve(numPixels);
    
    for (int i = 0; i < numPixels; ++i) {
        unsigned char rByte = data[3 * i + 0];
        unsigned char gByte = data[3 * i + 1];
        unsigned char bByte = data[3 * i + 2];

        // Normalize to [0, 1]
        float r = rByte / 255.0f;
        float g = gByte / 255.0f;
        float b = bByte / 255.0f;

        sumR += rByte;
        sumG += gByte;
        sumB += bByte;

        // HSV conversion
        float h, s, v;
        rgbToHsv(r, g, b, h, s, v);
        sumHue += h;  // H is in [0, 360]
        sumSat += s;  // S is in [0, 1]

        // Colorfulness: opponent color space (Hasler & Süsstrunk 2003)
        // rg = R - G
        // yb = 0.5 * (R + G) - B
        float rg = r - g;
        float yb = 0.5f * (r + g) - b;
        
        sumRG += rg;
        sumYB += yb;
        sumRG_sq += rg * rg;
        sumYB_sq += yb * yb;

        // Grayscale for contrast
        float gray = 0.299f * r + 0.587f * g + 0.114f * b;
        grayValues.push_back(gray);
    }

    stbi_image_free(data);

    // === Basic RGB features ===
    float avgR = static_cast<float>(sumR) / (255.0f * numPixels);
    float avgG = static_cast<float>(sumG) / (255.0f * numPixels);
    float avgB = static_cast<float>(sumB) / (255.0f * numPixels);
    float brightness = (avgR + avgG + avgB) / 3.0f;

    // === HSV features ===
    float hue = static_cast<float>(sumHue) / numPixels;  // Average hue in [0, 360]
    hue = hue / 360.0f;  // Normalize to [0, 1]
    
    float saturation = static_cast<float>(sumSat) / numPixels;  // Already [0, 1]

    // === Colorfulness metric ===
    // Mean and std dev of rg and yb
    float meanRG = static_cast<float>(sumRG) / numPixels;
    float meanYB = static_cast<float>(sumYB) / numPixels;
    
    float varianceRG = (static_cast<float>(sumRG_sq) / numPixels) - (meanRG * meanRG);
    float varianceYB = (static_cast<float>(sumYB_sq) / numPixels) - (meanYB * meanYB);
    
    float stdRG = std::sqrt(std::max(0.0f, varianceRG));
    float stdYB = std::sqrt(std::max(0.0f, varianceYB));
    
    // Colorfulness formula: sqrt(std_rg^2 + std_yb^2) + 0.3 * sqrt(mean_rg^2 + mean_yb^2)
    float colorfulness = std::sqrt(stdRG * stdRG + stdYB * stdYB) + 
                        0.3f * std::sqrt(meanRG * meanRG + meanYB * meanYB);
    
    // Normalize colorfulness: typical range is 0-100, clamp to [0, 1]
    colorfulness = std::min(colorfulness / 100.0f, 1.0f);

    // === Contrast: standard deviation of grayscale ===
    float meanGray = 0.0f;
    for (float g : grayValues) {
        meanGray += g;
    }
    meanGray /= numPixels;

    float varianceGray = 0.0f;
    for (float g : grayValues) {
        float diff = g - meanGray;
        varianceGray += diff * diff;
    }
    varianceGray /= numPixels;

    float contrast = std::sqrt(varianceGray);  // Already normalized to [0, 1] range

    return ImageFeatures{
        avgR, 
        avgG, 
        avgB, 
        brightness,
        hue,
        saturation,
        colorfulness,
        contrast
    };
}
