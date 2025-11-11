#!/bin/bash
# Script to generate simple placeholder ambience WAV files using SoX
# These are basic procedural sounds that can be replaced with better samples later

# Check if SoX is installed
if ! command -v sox &> /dev/null; then
    echo "SoX is not installed. Please install it first:"
    echo "  macOS: brew install sox"
    echo "  Ubuntu: sudo apt-get install sox"
    echo ""
    echo "Alternatively, download ambience samples manually from Freesound.org"
    exit 1
fi

AMBIENCE_DIR="$(dirname "$0")/../assets/ambience"
mkdir -p "$AMBIENCE_DIR"

echo "Generating placeholder ambience samples..."

# Ocean - pink noise with low-pass filter
echo "  - ocean.wav (pink noise filtered)"
sox -n -r 44100 -c 1 -b 16 "$AMBIENCE_DIR/ocean.wav" synth 10 pinknoise lowpass 800 gain -10 fade 0.5 10 0.5

# Rain - white noise with band-pass filter
echo "  - rain.wav (filtered white noise)"
sox -n -r 44100 -c 1 -b 16 "$AMBIENCE_DIR/rain.wav" synth 10 whitenoise band 2000 1000 gain -12 fade 0.5 10 0.5

# Forest - pink noise with birds (very basic)
echo "  - forest.wav (pink noise + tone)"
sox -n -r 44100 -c 1 -b 16 "$AMBIENCE_DIR/forest.wav" synth 10 pinknoise lowpass 1200 gain -15 : synth 10 sine 2000-3000 gain -25 : mix gain -5 fade 0.5 10 0.5

# City - brown noise (low rumble)
echo "  - city.wav (brown noise)"
sox -n -r 44100 -c 1 -b 16 "$AMBIENCE_DIR/city.wav" synth 10 brownnoise lowpass 300 gain -8 fade 0.5 10 0.5

# Room - very subtle pink noise
echo "  - room.wav (subtle pink noise)"
sox -n -r 44100 -c 1 -b 16 "$AMBIENCE_DIR/room.wav" synth 10 pinknoise gain -20 fade 0.5 10 0.5

echo ""
echo "✓ Placeholder ambience files generated in: $AMBIENCE_DIR"
echo ""
echo "These are basic procedural sounds. For better results, replace them with:"
echo "  - Real ocean wave recordings"
echo "  - Rain ambience"
echo "  - Forest recordings with birds"
echo "  - Urban ambience"
echo "  - Room tone"
echo ""
echo "Free sources: Freesound.org, BBC Sound Effects, etc."
