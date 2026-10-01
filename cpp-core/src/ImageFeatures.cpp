// Image bytes to the 8 features, in one pass over the pixels using running sums. stb_image does
// the JPEG and PNG decoding; anything it can't read becomes invalid_argument, which is a 400.
// Called from HttpServer.cpp /features (extractFeatures) and /compose (fromArray). Every formula
// here is mirrored in ml/features.py and checked against tests/feature_parity/golden.json.
// This define makes stb_image.h compile its function bodies here; it must be in one .cpp only.
#define STB_IMAGE_IMPLEMENTATION
#include "stb_image.h"

#include "ImageFeatures.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace {

// The paper's scale is 0-255, where about 100 is "extremely colorful".
constexpr double COLORFULNESS_SCALE = 255.0 / 100.0;

// BT.601, same as ml/features.py.
constexpr double LUMA_RED = 0.299, LUMA_GREEN = 0.587, LUMA_BLUE = 0.114;

constexpr long long MAX_PIXELS = 40'000'000;  // 120 MB of RGB once decoded

// The std dev of values in 0..1 can't go past 0.5.
constexpr size_t CONTRAST_INDEX = 7;
constexpr float MAX_CONTRAST = 0.5f;

// Std dev from running sums (variance is the mean of squares minus the squared mean), so no
// second pass is needed. Rounding can make the variance slightly negative.
double stdDev(double sum, double sumOfSquares, double count) {
  double mean = sum / count;
  return std::sqrt(std::max(0.0, sumOfSquares / count - mean * mean));
}

// Same as PIL's convert("HSV"), which ml/features.py uses.
void hueAndSaturation(double r, double g, double b, double& hue, double& saturation) {
  double maxChannel = std::max({r, g, b});
  double minChannel = std::min({r, g, b});
  double range = maxChannel - minChannel;

  // Black has no saturation; checking first avoids dividing by zero.
  saturation = maxChannel == 0.0 ? 0.0 : range / maxChannel;

  // Hue is worked out in sixths of the colour wheel: red is around 0, green around 2 and blue
  // around 4. A gray pixel has no hue, so it counts as 0.
  if (range == 0.0) {
    hue = 0.0;
  } else if (maxChannel == r) {
    hue = std::fmod((g - b) / range, 6.0);
  } else if (maxChannel == g) {
    hue = (b - r) / range + 2.0;
  } else {
    hue = (r - g) / range + 4.0;
  }
  // Divide by 6 to get 0 to 1. fmod keeps the sign, so reds leaning to blue come out slightly
  // negative and wrap round to just under 1.
  hue /= 6.0;
  if (hue < 0.0) hue += 1.0;
}

}  // namespace

// This order is the model's input order and the JSON order on the wire.
std::array<float, 8> ImageFeatures::toArray() const {
  return {avgRed, avgGreen, avgBlue, brightness, hue, saturation, colorfulness, contrast};
}

// /compose gets features as JSON from outside, so impossible values are rejected here.
ImageFeatures ImageFeatures::fromArray(const std::array<float, 8>& v) {
  // Written as !(in range) so NaN fails too. Contrast is the only feature with a 0.5 ceiling.
  // invalid_argument is what HttpServer.cpp turns into a 400.
  for (size_t i = 0; i < v.size(); ++i) {
    float max = i == CONTRAST_INDEX ? MAX_CONTRAST : 1.0f;
    if (!(v[i] >= 0.0f && v[i] <= max)) {
      throw std::invalid_argument("Feature " + std::to_string(i) + " must be between 0 and " +
                                  std::to_string(max));
    }
  }
  return {v[0], v[1], v[2], v[3], v[4], v[5], v[6], v[7]};
}

ImageFeatures extractFeatures(const std::string& imageBytes) {
  // stb_image wants unsigned bytes and an int length; the string is only a byte buffer here.
  const auto* data = reinterpret_cast<const unsigned char*>(imageBytes.data());
  const int size = static_cast<int>(imageBytes.size());
  int width = 0, height = 0, channels = 0;

  // Step 1: header check.
  // Check the size from the header before decoding, since a tiny file can claim to be
  // 100000x100000.
  if (!stbi_info_from_memory(data, size, &width, &height, &channels)) {
    throw std::invalid_argument(std::string("Could not decode image: ") + stbi_failure_reason());
  }
  // Multiplied as long long because two large ints would overflow an int.
  if (static_cast<long long>(width) * height > MAX_PIXELS) {
    throw std::invalid_argument("Image is larger than 40 megapixels");
  }

  // Step 2: decode.
  // The last argument asks for 3 channels, so PNGs with alpha or grayscale come back as RGB.
  // The result is width * height * 3 bytes laid out as R, G, B, R, G, B, ...
  unsigned char* pixels = stbi_load_from_memory(data, size, &width, &height, &channels, 3);
  if (!pixels) {
    throw std::invalid_argument(std::string("Could not decode image: ") + stbi_failure_reason());
  }

  // Step 3: running sums.
  // Plain sums give the means; the sums of squares give the std devs through stdDev above.
  // double keeps the rounding error small over as many as MAX_PIXELS pixels.
  double sumR = 0, sumG = 0, sumB = 0, sumHue = 0, sumSat = 0;
  double sumRG = 0, sumRGSq = 0, sumYB = 0, sumYBSq = 0, sumGray = 0, sumGraySq = 0;
  const double count = static_cast<double>(width) * height;

  for (long i = 0; i < static_cast<long>(count); ++i) {
    // Pixel i starts at byte 3 * i. Dividing by 255 puts each channel on 0 to 1, as
    // ml/features.py does.
    double r = pixels[3 * i] / 255.0;
    double g = pixels[3 * i + 1] / 255.0;
    double b = pixels[3 * i + 2] / 255.0;
    sumR += r;
    sumG += g;
    sumB += b;

    // Hue is averaged as a plain number, ignoring that red sits at both 0 and 1. Python does the
    // same, so the two still match.
    double hue, saturation;
    hueAndSaturation(r, g, b, hue, saturation);
    sumHue += hue;
    sumSat += saturation;

    // The two opponent colour axes the colourfulness metric is built on.
    double redGreen = r - g;
    double yellowBlue = 0.5 * (r + g) - b;
    sumRG += redGreen;
    sumRGSq += redGreen * redGreen;
    sumYB += yellowBlue;
    sumYBSq += yellowBlue * yellowBlue;

    // Grayscale is only needed for contrast.
    double gray = LUMA_RED * r + LUMA_GREEN * g + LUMA_BLUE * b;
    sumGray += gray;
    sumGraySq += gray * gray;
  }
  // stb allocated the pixels with malloc, so they are freed through stb, not delete.
  stbi_image_free(pixels);

  // Step 4: final maths.
  // Hasler and Suesstrunk: how spread out the opponent values are, plus 0.3 times how far their
  // mean is from gray.
  double spread = std::hypot(stdDev(sumRG, sumRGSq, count), stdDev(sumYB, sumYBSq, count));
  double offset = std::hypot(sumRG / count, sumYB / count);
  // Rescaled so 100 on the paper's scale is 1, then capped at 1 like ml/features.py.
  double colorfulness = std::min((spread + 0.3 * offset) * COLORFULNESS_SCALE, 1.0);

  // Means are sums over the pixel count. Brightness is the mean of the three channel means, the
  // same as ml/features.py.
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
