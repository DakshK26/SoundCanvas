#!/bin/bash

# Test the full pipeline - creates separate MIDI stems and renders them

set -e

IMAGE="${1:-../ml/data/raw_images/image_01500.jpg}"
STEMS_DIR="/tmp/soundcanvas_stems"
OUTPUT_DIR="/Users/karankardam/SoundCanvas/SoundCanvas/output"

echo "========================================="
echo "SoundCanvas Full Pipeline Test"
echo "========================================="
echo ""
echo "Image: $IMAGE"
echo "Stems directory: $STEMS_DIR"
echo ""

# Create directories
mkdir -p "$STEMS_DIR"
mkdir -p "$OUTPUT_DIR"

# Step 1: Generate separate MIDI stems
echo "[1/3] Composing separate MIDI stems..."
cd ../cpp-core/build

# Use a simple test: just create stems manually for now
# TODO: Implement proper --stems-only mode
echo "  Generating combined MIDI first..."
./soundcanvas_core --compose-only "$IMAGE" "$STEMS_DIR/full.mid"

echo ""
echo "✅ MIDI generated!"
echo ""

# Step 2: Render each stem to WAV using FluidSynth
echo "[2/3] Rendering MIDI stems to WAV..."

SF2="/opt/homebrew/Cellar/fluid-synth/2.5.1/share/fluid-synth/sf2/VintageDreamsWaves-v2.sf2"

if [ ! -f "$SF2" ]; then
    echo "Error: Soundfont not found at $SF2"
    echo "Install with: brew install fluid-synth"
    exit 1
fi

echo "  Rendering full MIDI with FluidSynth..."
fluidsynth -F "$OUTPUT_DIR/rendered_audio.wav" -r 44100 -g 1.0 "$SF2" "$STEMS_DIR/full.mid" 2>&1 | grep -i "rendering" || true

echo ""
echo "✅ Audio rendered!"
echo ""

# Step 3: Show results
echo "[3/3] Results"
echo "========================================="
echo ""
echo "Generated files:"
ls -lh "$STEMS_DIR"/*.mid 2>/dev/null || echo "  No MIDI files"
echo ""
ls -lh "$OUTPUT_DIR"/rendered_audio.wav
echo ""

FILE_SIZE=$(du -h "$OUTPUT_DIR/rendered_audio.wav" | awk '{print $1}')
echo "✅ Full pipeline test complete!"
echo ""
echo "Output: $OUTPUT_DIR/rendered_audio.wav ($FILE_SIZE)"
echo ""
echo "Play with: afplay $OUTPUT_DIR/rendered_audio.wav"
echo ""
echo "Note: This used basic rendering. For professional quality:"
echo "  1. Start audio-producer: cd ../infra && docker-compose up audio-producer -d"
echo "  2. Run: ./soundcanvas_core --full-pipeline $IMAGE output.wav"
echo ""
