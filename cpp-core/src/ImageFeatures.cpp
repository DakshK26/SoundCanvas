#define STB_IMAGE_IMPLEMENTATION
#include "stb_image.h"

#include "ImageFeatures.hpp"
#include <stdexcept>
#include <cmath>

ImageFeatures extractImageFeatures(const std::string& imagePath) {
    int width, height, channels;
    unsigned char* data = stbi_load(imagePath.c_str(), &width, &height, &channels, 3);
    if (!data) {
        throw std::runtime_error("Failed to load image: " + imagePath);
    }

    const int numPixels = width * height;
    long long sumR = 0, sumG = 0, sumB = 0;

    for (int i = 0; i < numPixels; ++i) {
        unsigned char r = data[3 * i + 0];
        unsigned char g = data[3 * i + 1];
        unsigned char b = data[3 * i + 2];

        sumR += r;
        sumG += g;
        sumB += b;
    }

    stbi_image_free(data);

    float avgR = static_cast<float>(sumR) / (255.0f * numPixels);
    float avgG = static_cast<float>(sumG) / (255.0f * numPixels);
    float avgB = static_cast<float>(sumB) / (255.0f * numPixels);

    float brightness = (avgR + avgG + avgB) / 3.0f;

    return ImageFeatures{avgR, avgG, avgB, brightness};
}
