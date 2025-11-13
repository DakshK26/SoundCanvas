# Phase 9 Setup Guide

Quick setup instructions for Phase 9 (Genre & Production Diversity).

## Prerequisites

- **Python 3.8+** (for audio-producer)
- **CMake 3.15+** (for cpp-core)
- **C++ Compiler** (MSVC on Windows, GCC/Clang on Linux)
- **FluidSynth** (for MIDI rendering)

## Installation Steps

### 1. Install Python Dependencies

```bash
cd audio-producer
pip install -r requirements.txt
```

**Phase 9 packages:**
- `mido` - MIDI file parsing (for kick detection, FX timing)
- `soundfile` - WAV/OGG file I/O (for sample loading)
- `pyyaml` - YAML config parsing (for drum kits, mix presets)
- `requests` - HTTP client (for Freesound API)

### 2. Build C++ Core

**Windows (PowerShell):**
```powershell
cd cpp-core
mkdir build
cd build
cmake ..
cmake --build . --config Release
```

**Linux/Mac:**
```bash
cd cpp-core
mkdir build && cd build
cmake ..
make -j4
```

**Verify Build:**
```bash
# Windows
.\build\Release\soundcanvas.exe --help

# Linux/Mac
./build/soundcanvas --help
```

### 3. Configure Freesound API (Optional)

Sample-based drums use the Freesound API. If you want to download authentic drum samples:

1. Create account at https://freesound.org/
2. Get API key from https://freesound.org/apiv2/apply/
3. Create `config/freesound.json`:

```json
{
  "Client_id": "YUNc0D9lUoGDbNMfHVN7",
  "Api_key": "YOUR_API_KEY_HERE"
}
```

4. Download samples:

```bash
python tools/fetch_freesound_assets.py --kit trap_808
python tools/fetch_freesound_assets.py --kit house
python tools/fetch_freesound_assets.py --kit rnb_soft
python tools/fetch_freesound_assets.py --fx all
```

**Note:** Freesound API has rate limits (50 requests/day for free tier). If downloads fail, the drum sampler will use procedural fallbacks.

### 4. Test Phase 9

```bash
# Test with 3 random images from ml/data/raw_images/
python scripts/test_phase9.py
```

**Expected Output:**
```
=====================================================
Phase 9 Test Script
Testing genre diversity with 3 random images
=====================================================

Selected 3 random images:
  - ml/data/raw_images/sunset.jpg
  - ml/data/raw_images/cityscape.jpg
  - ml/data/raw_images/nature.jpg

============================================================
Testing: phase9_test1
Image: ml/data/raw_images/sunset.jpg
============================================================

[1] Generating MIDI from image...
Genre: HOUSE
Tempo: 124 BPM
✓ MIDI created: output/phase9_test1.mid

[2] Rendering audio with Phase 9 pipeline...
  Rendering drums with house kit...
    ✓ Drums: output/phase9_test1_drums.wav
  Rendering FX (duration: 67.5s)...
    ✓ FX: output/phase9_test1_fx.wav
  Mixing stems...
    ✓ Mixed: output/phase9_test1_temp.wav
  Mastering...
    ✓ Final: output/phase9_test1.wav

✓ Test complete: output/phase9_test1.wav

...

=====================================================
Test Summary
=====================================================
✓ PASS  phase9_test1
✓ PASS  phase9_test2
✓ PASS  phase9_test3

Passed: 3/3

✓ All tests passed! Check output/ folder for results.
```

### 5. Verify Outputs

Listen to the generated tracks and verify:

- **Genre Differences**: Rap sounds different from House, which sounds different from R&B
- **Sample-Based Drums**: Drums sound punchy and realistic (not GM soundfont)
- **Sidechain Pumping**: Bass/melodic instruments duck when kick hits
- **FX Transitions**: Uplifters before drops, impacts at section starts

---

## Troubleshooting

### "Import 'mido' could not be resolved"

**Solution:**
```bash
pip install mido soundfile pyyaml requests
```

### "C++ executable not found"

**Solution:** Build the C++ core first:
```bash
cd cpp-core
mkdir build && cd build
cmake .. && cmake --build . --config Release
```

### "No images found in ml/data/raw_images/"

**Solution:** Download sample images:
```bash
cd ml
python src/download_images.py
```

### "Freesound API rate limit exceeded"

**Solution:** 
- Wait 24 hours for rate limit reset
- Use procedural drum sounds (automatic fallback)
- Upgrade to Freesound premium account

### "FluidSynth not found"

**Windows:**
```powershell
# Install via Chocolatey
choco install fluidsynth

# Or download from https://github.com/FluidSynth/fluidsynth/releases
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install fluidsynth
```

**Mac:**
```bash
brew install fluid-synth
```

---

## Quick Start (Docker)

If you prefer Docker:

```bash
# Build all services
docker-compose build

# Start services
docker-compose up

# Test via API
curl -X POST http://localhost:9000/generate \
  -F "image=@test.jpg" \
  -F "genre=HOUSE"
```

---

## File Locations

After setup, you should have:

```
SoundCanvas/
├── audio-producer/
│   ├── assets/
│   │   ├── kits/          # Drum kit configs (YAML)
│   │   ├── samples/       # Downloaded samples (WAV/OGG)
│   │   │   ├── trap_808/
│   │   │   ├── house/
│   │   │   └── rnb_soft/
│   │   └── fx/
│   │       ├── uplifters/
│   │       ├── downlifters/
│   │       └── impacts/
│   └── mix/
│       └── presets/       # Mix presets (YAML)
│           ├── rap.yaml
│           ├── house.yaml
│           └── rnb.yaml
│
├── cpp-core/
│   └── build/
│       └── Release/       # Built executable
│           └── soundcanvas.exe
│
├── output/                # Test outputs
│   ├── phase9_test1.mid
│   ├── phase9_test1.wav
│   ├── phase9_test2.mid
│   ├── phase9_test2.wav
│   └── ...
│
└── config/
    └── freesound.json     # API credentials
```

---

## Next Steps

1. **Listen to outputs** in `output/` folder
2. **Tweak mix presets** in `audio-producer/mix/presets/*.yaml`
3. **Download more samples** with `fetch_freesound_assets.py`
4. **Test different images** to hear genre variety
5. **Integrate with frontend** (React UI for genre selection)

---

## Support

For issues or questions:
- Check `docs/PHASE9_COMPLETE.md` for detailed documentation
- Review Python lint errors (missing packages = expected before install)
- Test incrementally (C++ → MIDI → Audio → Mix → Master)

**Phase 9 Status**: ✓ Complete and ready for testing!
