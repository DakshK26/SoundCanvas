// The 8 numbers an image is reduced to. They are the model's input and also shape the song.
// Must match ml/features.py, which built the training set; tests/feature_parity checks this.
// Computed in ImageFeatures.cpp, called from HttpServer.cpp /features and /compose.
#pragma once

#include <array>
#include <string>

struct ImageFeatures {
  // Mean colour of the photo
  float avgRed;        // 0 to 1
  float avgGreen;      // 0 to 1
  float avgBlue;       // 0 to 1
  float brightness;    // 0 to 1, mean of the three above

  // Colour character, averaged per pixel
  float hue;           // 0 to 1
  float saturation;    // 0 to 1
  float colorfulness;  // 0 to 1, Hasler and Suesstrunk 2003
  float contrast;      // 0 to 0.5, std dev of grayscale

  // The model's input order. Must match FEATURE_NAMES in ml/features.py.
  std::array<float, 8> toArray() const;
  // The reverse, for /compose. Throws std::invalid_argument if a value is out of its range.
  static ImageFeatures fromArray(const std::array<float, 8>& values);
};

// Throws std::invalid_argument if the bytes aren't a usable JPEG or PNG.
ImageFeatures extractFeatures(const std::string& imageBytes);
