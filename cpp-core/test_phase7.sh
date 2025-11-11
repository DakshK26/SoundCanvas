#!/bin/bash
# Quick test script for Phase 7 Person B implementation

set -e

echo "========================================"
echo "Phase 7 Person B - Quick Test"
echo "========================================"
echo ""

# Check if build exists
if [ ! -f "build/soundcanvas_core" ]; then
    echo "❌ Binary not found. Building first..."
    cd build && make && cd ..
fi

# Create test output directory
mkdir -p test_output

echo "Testing Phase 7 features with a simple test..."
echo ""

# Test with heuristic mode (no model needed)
echo "1. Testing heuristic mode (no TF Serving required)..."

# Create a simple test that shows the new parameters
echo "   Creating test image features..."

# Run with any existing image or create a dummy test
if [ -f "../examples/ocean.jpg" ]; then
    TEST_IMAGE="../examples/ocean.jpg"
elif [ -f "examples/test.jpg" ]; then
    TEST_IMAGE="examples/test.jpg"
else
    echo "   ⚠️  No test image found in ../examples/ or examples/"
    echo "   Please provide an image to test, or the system will use procedural generation"
    echo ""
    echo "   To test manually, run:"
    echo "   ./build/soundcanvas_core --mode=heuristic YOUR_IMAGE.jpg test_output/test.wav"
    echo ""
    echo "   The output will show:"
    echo "   - Music parameters (7-dim)"
    echo "   - Style parameters (Phase 7): ambience, instrument, mood"
    echo ""
    exit 0
fi

echo "   Using test image: $TEST_IMAGE"
echo ""

./build/soundcanvas_core --mode=heuristic "$TEST_IMAGE" test_output/phase7_test.wav

echo ""
echo "========================================"
echo "✓ Phase 7 Test Complete"
echo "========================================"
echo ""
echo "Check test_output/phase7_test.wav"
echo ""
echo "The console output above should show:"
echo "  - Music parameters (7-dim)"
echo "  - Style parameters (Phase 7):"
echo "    * ambienceType (0-4)"
echo "    * instrumentPreset (0-3)"
echo "    * moodScore (0.0-1.0)"
echo ""
echo "Audio features in the WAV:"
echo "  - Instrument preset sounds (4 types)"
echo "  - Optional melody layer (if energy/mood high enough)"
echo "  - Ambience background (or procedural fallback)"
echo "  - Mood-adjusted reverb and mixing"
echo ""
