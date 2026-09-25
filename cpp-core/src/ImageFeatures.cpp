// Measures an image's 8 features in one pass over its pixels.
// Must stay in sync with ml/features.py, which the model was trained on.
#define STB_IMAGE_IMPLEMENTATION
#include "stb_image.h"

#include "ImageFeatures.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace {

// Hasler and Suesstrunk define colorfulness on 0-255 pixel values, where about
// 100 already means "extremely colorful". We scale by that so the result is 0 to 1.
constexpr double COLORFULNESS_SCALE = 255.0 / 100.0;

// ITU-R BT.601 luma weights: how bright each channel looks to the human eye.
constexpr double LUMA_RED = 0.299, LUMA_GREEN = 0.587, LUMA_BLUE = 0.114;

// Phone cameras top out around 50 MP but save at 12 MP by default; 40 MP decodes to 120 MB of RGB.
constexpr long long MAX_PIXELS = 40'000'000;

// Returns the standard deviation from a running sum and sum of squares.
double stdDev(double sum, double sumOfSquares, double count) {
  double mean = sum / count;
  return std::sqrt(std::max(0.0, sumOfSquares / count - mean * mean));
}

// Returns the HSV hue (0 to 1) and saturation (0 to 1) of one pixel.
void hueAndSaturation(double r, double g, double b, double& hue, double& saturation) {
  double maxChannel = std::max({r, g, b});
  double minChannel = std::min({r, g, b});
  double range = maxChannel - minChannel;

  saturation = maxChannel == 0.0 ? 0.0 : range / maxChannel;

  if (range == 0.0) {
    hue = 0.0;
  } else if (maxChannel == r) {
    hue = std::fmod((g - b) / range, 6.0);
  } else if (maxChannel == g) {
    hue = (b - r) / range + 2.0;
  } else {
    hue = (r - g) / range + 4.0;
  }
  hue /= 6.0;  // the color wheel has six 60-degree sectors
  if (hue < 0.0) hue += 1.0;
}

}  // namespace

std::array<float, 8> ImageFeatures::toArray() const {
  return {avgRed, avgGreen, avgBlue, brightness, hue, saturation, colorfulness, contrast};
}

ImageFeatures ImageFeatures::fromArray(const std::array<float, 8>& v) {
  return {v[0], v[1], v[2], v[3], v[4], v[5], v[6], v[7]};
}

ImageFeatures extractFeatures(const std::string& imageBytes) {
  const auto* data = reinterpret_cast<const unsigned char*>(imageBytes.data());
  const int size = static_cast<int>(imageBytes.size());
  int width = 0, height = 0, channels = 0;

  // Read the header first: a small file can claim huge dimensions and exhaust memory when decoded.
  if (!stbi_info_from_memory(data, size, &width, &height, &channels)) {
    throw std::invalid_argument(std::string("Could not decode image: ") + stbi_failure_reason());
  }
  if (static_cast<long long>(width) * height > MAX_PIXELS) {
    throw std::invalid_argument("Image is larger than 40 megapixels");
  }

  unsigned char* pixels = stbi_load_from_memory(data, size, &width, &height, &channels, 3);
  if (!pixels) {
    throw std::invalid_argument(std::string("Could not decode image: ") + stbi_failure_reason());
  }

  double sumR = 0, sumG = 0, sumB = 0, sumHue = 0, sumSat = 0;
  double sumRG = 0, sumRGSq = 0, sumYB = 0, sumYBSq = 0, sumGray = 0, sumGraySq = 0;
  const double count = static_cast<double>(width) * height;

  for (long i = 0; i < static_cast<long>(count); ++i) {
    double r = pixels[3 * i] / 255.0;
    double g = pixels[3 * i + 1] / 255.0;
    double b = pixels[3 * i + 2] / 255.0;
    sumR += r;
    sumG += g;
    sumB += b;

    double hue, saturation;
    hueAndSaturation(r, g, b, hue, saturation);
    sumHue += hue;
    sumSat += saturation;

    // Colorfulness uses two "opponent" color axes: red vs green, and yellow vs blue.
    double redGreen = r - g;
    double yellowBlue = 0.5 * (r + g) - b;
    sumRG += redGreen;
    sumRGSq += redGreen * redGreen;
    sumYB += yellowBlue;
    sumYBSq += yellowBlue * yellowBlue;

    double gray = LUMA_RED * r + LUMA_GREEN * g + LUMA_BLUE * b;
    sumGray += gray;
    sumGraySq += gray * gray;
  }
  stbi_image_free(pixels);

  double spread = std::hypot(stdDev(sumRG, sumRGSq, count), stdDev(sumYB, sumYBSq, count));
  double offset = std::hypot(sumRG / count, sumYB / count);
  double colorfulness = std::min((spread + 0.3 * offset) * COLORFULNESS_SCALE, 1.0);

  ImageFeatures features;
  features.avgRed = static_cast<float>(sumR / count);
  features.avgGreen = static_cast<float>(sumG / count);
  features.avgBlue = static_cast<float>(sumB / count);
  features.brightness = (features.avgRed + features.avgGreen + features.avgBlue) / 3.0f;
  features.hue = static_cast<float>(sumHue / count);
  features.saturation = static_cast<float>(sumSat / count);
  features.colorfulness = static_cast<float>(colorfulness);
  features.contrast = static_cast<float>(stdDev(sumGray, sumGraySq, count));
  return features;
}
