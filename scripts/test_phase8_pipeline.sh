#!/bin/bash
#
# Phase 8 Integration Test Script
# Tests Person A (Composition) + Person B (Rendering) pipeline
#

set -e

echo "========================================="
echo "Phase 8: Full Pipeline Integration Test"
echo "========================================="
echo ""

# Configuration
IMAGE="${1:-../ml/data/raw_images/image_00001.jpg}"
OUTPUT_DIR="${2:-/tmp/phase8_output}"
SOUNDFONT="/usr/share/sounds/sf2/FluidR3_GM.sf2"

mkdir -p "$OUTPUT_DIR"

echo "Input image: $IMAGE"
echo "Output directory: $OUTPUT_DIR"
echo ""

# Step 1: Person A - Composition
echo "[1/2] Person A: Composing multi-track MIDI..."
echo "-------------------------------------------"

cd ../cpp-core/build

./soundcanvas_core --compose-only "$IMAGE" "$OUTPUT_DIR/composition.mid" | \
    grep -E "(Song Specification|Tempo|Scale|Groove|Sections|Tracks|Composing)"

echo ""
echo "✅ Composition complete"
echo ""

# Step 2: Person B - Rendering & Mixing
echo "[2/2] Person B: Rendering with effects..."
echo "-------------------------------------------"

cd ../../scripts

python3 render_pipeline.py "$OUTPUT_DIR/composition.mid" "$OUTPUT_DIR/final_mix.wav" DRIVING

echo ""

# Results
echo "========================================="
echo "Pipeline Complete! 🎵"
echo "========================================="
echo ""
echo "Generated files:"
ls -lh "$OUTPUT_DIR"/*.mid "$OUTPUT_DIR"/*.wav
echo ""

DURATION=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$OUTPUT_DIR/final_mix.wav" 2>/dev/null || echo "unknown")
echo "Final track duration: ${DURATION}s"
echo ""
echo "Play with:"
echo "  afplay $OUTPUT_DIR/final_mix.wav"
echo "  or"
echo "  aplay $OUTPUT_DIR/final_mix.wav"
echo ""
