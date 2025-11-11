#!/bin/bash

# SoundCanvas Full Pipeline Test
# Tests Person A (composition) + Person B (production) integration

set -e

echo "========================================="
echo "SoundCanvas Full Pipeline Test"
echo "Person A: Composition | Person B: Production"
echo "========================================="
echo

# Configuration
TEST_IMAGE="${1:-../ml/data/raw_images/image_00123.jpg}"
OUTPUT_DIR="/tmp/soundcanvas_test"
MIDI_OUTPUT="$OUTPUT_DIR/composition.mid"
AUDIO_OUTPUT="$OUTPUT_DIR/final_track.wav"

# Create output directory
mkdir -p "$OUTPUT_DIR"

echo "Step 1: Compose MIDI from Image"
echo "  Image: $TEST_IMAGE"
echo "  Output: $MIDI_OUTPUT"
echo

cd ../cpp-core/build

./soundcanvas_core --compose-only "$TEST_IMAGE" "$MIDI_OUTPUT"

echo
echo "✅ MIDI composition complete!"
echo

# Check if audio-producer service is running
if curl -s http://localhost:9001/health > /dev/null 2>&1; then
    echo "Step 2: Produce Audio (Person B's audio-producer service)"
    echo "  Input: $MIDI_OUTPUT"
    echo "  Output: $AUDIO_OUTPUT"
    echo
    
    # Call audio-producer service
    # Note: This assumes the MIDI has been split into stems by Person A
    # For now, we'll just show what the call would look like
    
    echo "Would call audio-producer with:"
    echo '{'
    echo '  "stems": {'
    echo '    "full": "'$MIDI_OUTPUT'"'
    echo '  },'
    echo '  "output_path": "'$AUDIO_OUTPUT'",'
    echo '  "genre": "EDM_Chill",'
    echo '  "apply_mastering": true,'
    echo '  "apply_sidechain": false'
    echo '}'
    echo
    echo "Note: Full multi-stem production requires Person A to generate"
    echo "      separate MIDI files for kick, bass, lead, etc."
else
    echo "Step 2: Audio-producer service not running"
    echo "  To test full pipeline:"
    echo "    cd ../infra && docker-compose up audio-producer -d"
    echo
fi

echo
echo "========================================="
echo "Test Complete!"
echo "========================================="
echo
echo "Generated files:"
echo "  MIDI: $MIDI_OUTPUT"
if [ -f "$AUDIO_OUTPUT" ]; then
    echo "  Audio: $AUDIO_OUTPUT"
    echo
    echo "Play with: afplay $AUDIO_OUTPUT"
fi
echo
echo "What was tested:"
echo "  ✅ Person A: Image → Features → MIDI Composition"
echo "  ⏳ Person B: MIDI Stems → Mixed & Mastered WAV"
echo "     (requires audio-producer service running)"
echo
