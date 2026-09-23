// The 8 numbers that describe an image's color and mood.
// ml/features.py computes the same 8 in Python to build the training data.
#pragma once

#include <array>
#include <string>

struct ImageFeatures {
  float avgRed;        // 0 to 1
  float avgGreen;      // 0 to 1
  float avgBlue;       // 0 to 1
  float brightness;    // 0 to 1, mean of the three channel averages
  float hue;           // 0 to 1 around the color wheel (0 = red, 0.33 = green, 0.66 = blue)
  float saturation;    // 0 to 1
  float colorfulness;  // 0 to 1, Hasler and Suesstrunk (2003)
  float contrast;      // 0 to 0.5, spread of grayscale brightness

  // The features in the order the ml model expects.
  std::array<float, 8> toArray() const;
  static ImageFeatures fromArray(const std::array<float, 8>& values);
};

// Decodes a JPG or PNG from raw bytes and measures its 8 features.
ImageFeatures extractFeatures(const std::string& imageBytes);
