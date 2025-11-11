#!/bin/bash
# Setup ambience files for audio renderer
# This copies the existing ambience files from cpp-core to the shared data volume

set -e

SCRIPT_DIR="$(dirname "$0")"
CPP_CORE_AMBIENCE="$SCRIPT_DIR/../cpp-core/assets/ambience"
DATA_AMBIENCE="$SCRIPT_DIR/../data/ambience"

echo "Setting up ambience files for audio renderer..."

# Create data/ambience directory
mkdir -p "$DATA_AMBIENCE"

# Check if cpp-core ambience files exist
if [ -d "$CPP_CORE_AMBIENCE" ]; then
    echo "Copying ambience files from cpp-core/assets/ambience..."
    
    for file in ocean.wav rain.wav forest.wav city.wav room.wav; do
        if [ -f "$CPP_CORE_AMBIENCE/$file" ]; then
            echo "  ✓ Copying $file"
            cp "$CPP_CORE_AMBIENCE/$file" "$DATA_AMBIENCE/"
        else
            echo "  ⚠ $file not found, will be generated procedurally"
        fi
    done
else
    echo "⚠ cpp-core/assets/ambience not found"
    echo "Ambience files will be generated procedurally by the audio renderer"
fi

echo ""
echo "Ambience setup complete."
echo "Files in $DATA_AMBIENCE:"
ls -lh "$DATA_AMBIENCE" 2>/dev/null || echo "  (none - will use procedural fallback)"
