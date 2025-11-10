#include "ImageFeatures.hpp"
#include <cassert>
#include <iostream>

int main() {
    // Use a tiny test image you create manually later
    try {
        ImageFeatures f = extractImageFeatures("test_data/solid_red.png");
        assert(f.avgR > 0.8f);
        std::cout << "ImageFeatures test passed\n";
    } catch (...) {
        std::cout << "ImageFeatures test failed\n";
        return 1;
    }
    return 0;
}
