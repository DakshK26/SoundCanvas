// the 8 numbers I boil an image down to.
// NOTE: ml/features.py does the exact same math in python for the training set.
// if one changes the other has to change too (tests/feature_parity checks this)
#pragma once

#include <array>
#include <string>

struct ImageFeatures {
  float avgRed;        // 0 to 1
  float avgGreen;      // 0 to 1
  float avgBlue;       // 0 to 1
  float brightness;    // 0 to 1, just avg of the 3 above
  float hue;           // 0 to 1 around the wheel (0 red, .33 green, .66 blue)
  float saturation;    // 0 to 1
  float colorfulness;  // 0 to 1, Hasler & Suesstrunk 2003 metric
  float contrast;      // 0 to 0.5 (std dev of grayscale, can't go past .5)

  // order matters!! this is the order the model was trained on
  std::array<float, 8> toArray() const;
  static ImageFeatures fromArray(const std::array<float, 8>& values);
};

// raw jpg/png bytes -> features. throws invalid_argument on junk input
ImageFeatures extractFeatures(const std::string& imageBytes);
