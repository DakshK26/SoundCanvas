# Phase 9: Genre & Production Diversity - COMPLETE ✓

**Status**: Implementation complete  
**Date**: January 2025  
**Objective**: Add genre diversity (Rap, House, R&B) with distinct production characteristics

---

## Overview

Phase 9 enhances SoundCanvas with **genre-specific composition and production**:

### Person A: Composition Diversity (C++ Core) ✓
- **5 Genres**: EDM_CHILL, EDM_DROP, HOUSE, RAP, RNB
- **Swing Timing**: Triplet/shuffle grooves for R&B/Hip-Hop
- **Drum Patterns**: Genre-specific patterns (Trap 808s, House kicks, R&B soft drums)
- **Chord Progressions**: Genre-aware harmony (minor for Rap, major 7ths for House, jazz for R&B)
- **Section Activity**: Varied density (Rap intro simple, House drop dense)

### Person B: Audio Production (Python Pipeline) ✓
- **Sample-Based Drums**: Freesound API integration, WAV one-shots, velocity layers
- **Genre-Aware Mixing**: YAML presets with EQ/compression/reverb per genre
- **MIDI-Based Sidechain**: Precise kick timing from MIDI (not audio peak detection)
- **FX Player**: Uplifters, downlifters, impacts at section boundaries
- **Complete Integration**: Updated audio-producer service with all Phase 9 features

---

## Person A Implementation (C++ Core)

### 1. Genre System

**Files Modified:**
- `cpp-core/include/SongSpec.hpp` - Genre enum and structs
- `cpp-core/src/SongSpec.cpp` - Genre selection logic
- `cpp-core/src/Composer.cpp` - Genre-aware composition
- `cpp-core/src/main.cpp` - Genre display

**Genre Types:**
```cpp
enum class Genre {
    EDM_CHILL,   // Ambient, chill vibes
    EDM_DROP,    // High energy drops
    HOUSE,       // Four-on-floor, pumping
    RAP,         // Trap-style, sparse
    RNB          // Smooth, syncopated
};
```

**Genre Selection:**
- Based on image features (brightness, saturation, energy)
- Deterministic seed-based randomness
- Genre profiles with tempo, density, swing characteristics

### 2. Swing Timing

**Implementation:**
```cpp
void applySwing(std::vector<NoteEvent>& notes, float swingAmount, int division)
```

- **Division 8**: Quantize to 8th notes, shift off-beats
- **Division 12**: Triplet feel (R&B shuffle)
- **Amount**: 0.0 (none) to 1.0 (maximum swing)

**Genre Swing:**
- **R&B**: 0.4 swing on 12th notes (triplet feel)
- **Rap**: 0.2 swing on 8th notes (slight bounce)
- **House/EDM**: 0.0 swing (quantized)

### 3. Drum Patterns

**Patterns Implemented:**
- `getHousePattern()` - Four-on-floor kicks, offbeat hats
- `getTrapPattern()` - Sparse kicks, snare rolls, rapid hats
- `getRnBPattern()` - Syncopated kicks, ghost snares

**Pattern Structure:**
```cpp
struct DrumPattern {
    std::vector<int> kick_ticks;
    std::vector<int> snare_ticks;
    std::vector<int> hihat_ticks;
};
```

### 4. Chord Progressions

**Genre-Specific Harmony:**
```cpp
std::vector<Chord> getGenreChords(Genre genre, int key);
```

- **Rap**: Minor progressions (i - iv - v - i)
- **House**: Extended chords (Imaj7 - VIm7 - IVmaj7)
- **R&B**: Jazz-influenced (ii7 - V7 - Imaj7)

### 5. Section Activity

**Density Control:**
```cpp
struct SectionActivity {
    float melody_density;   // 0.0 - 1.0
    float harmony_density;  // 0.0 - 1.0
    float rhythm_density;   // 0.0 - 1.0
};
```

**Example (Rap Intro):**
- Melody: 0.3 (sparse, simple)
- Harmony: 0.5 (basic chords)
- Rhythm: 0.4 (minimal drums)

**Example (House Drop):**
- Melody: 0.9 (dense leads)
- Harmony: 0.8 (full chords)
- Rhythm: 1.0 (maximum energy)

---

## Person B Implementation (Python Audio Producer)

### 1. Sample-Based Drums

**File:** `audio-producer/drum_sampler.py`

**Features:**
- Load WAV drum samples from disk
- YAML kit configs with MIDI mappings
- Round-robin/random/velocity-based sample selection
- Render MIDI to multi-track WAV

**Kit Configs:**
```yaml
# trap_808.yaml
kit_name: "Trap 808 Kit"
freesound_tags:
  - "808 kick"
  - "trap snare"
  - "hi-hat electronic"

samples:
  36:  # Kick
    freesound_tags: ["808 kick", "bass drum electronic"]
    velocity_layers: [0-80: soft, 81-127: hard]
```

**Usage:**
```python
sampler = DrumSampler(kits_dir='assets/kits', samples_dir='assets/samples')
sampler.render_midi('composition.mid', 'drums.wav', kit_name='trap_808')
```

### 2. Freesound Asset Fetcher

**File:** `tools/fetch_freesound_assets.py`

**Features:**
- Search Freesound API with tags
- Download samples (WAV/OGG/FLAC)
- Rate limiting (50 requests/day)
- Metadata tracking (JSON manifest)

**Usage:**
```bash
python tools/fetch_freesound_assets.py --kit trap_808
python tools/fetch_freesound_assets.py --fx all
```

**API Config:** `config/freesound.json`

### 3. Genre-Aware Mixing

**File:** `audio-producer/mix/schema.py`

**Mix Preset Structure:**
```yaml
# rap.yaml
buses:
  drums:
    gain: 1.0
    eq_low_boost: 3.0    # Boost sub bass
    eq_mid_cut: -2.0     # Cut muddy mids
    eq_high_boost: 2.0   # Crisp hats
    compression:
      threshold: -10.0
      ratio: 4.0
      attack: 5.0
      release: 50.0
  
master:
  sidechain_amount: 0.6  # Heavy pumping
  reverb_wet: 0.1        # Dry mix
  limiter_threshold: -1.0
```

**Genres:**
- `rap.yaml` - Heavy bass, dry, aggressive compression
- `house.yaml` - Pumping sidechain, bright highs, spacious reverb
- `rnb.yaml` - Warm mids, subtle compression, lush reverb

### 4. MIDI-Based Sidechain

**File:** `audio-producer/stem_mixer.py` (enhanced)

**Old Approach:**
- Analyze kick WAV audio
- Detect peaks
- Generate envelope

**New Approach (Phase 9):**
```python
def parse_kick_events_from_midi(midi_path: str) -> List[float]:
    """Extract kick note-on events (note 35/36, channel 9)"""
    kick_times = []
    for msg in midi_track:
        if msg.type == 'note_on' and msg.note in [35, 36]:
            kick_times.append(current_time)
    return kick_times
```

**Benefits:**
- Precise timing (no peak detection errors)
- Works before audio rendering
- Adjustable attack/hold/release

### 5. FX Player

**File:** `audio-producer/fx_player.py`

**Features:**
- Load Freesound FX samples (uplifters, downlifters, impacts)
- Procedural fallbacks (white noise sweeps, sine impacts)
- Parse MIDI metadata for section boundaries
- Render FX stem synchronized to song structure

**Procedural Generation:**
```python
# Uplifter: white noise bandpass sweep
def generate_uplifter(duration: float) -> np.ndarray:
    noise = np.random.randn(samples)
    freqs = np.logspace(np.log10(200), np.log10(8000), samples)
    filtered = apply_sweeping_bandpass(noise, freqs)
    return filtered * exponential_envelope
```

### 6. Pipeline Integration

**File:** `audio-producer/app.py` (updated)

**New `/produce` Endpoint:**
```json
POST /produce
{
  "midi_path": "/data/composition.mid",
  "genre": "HOUSE",
  "use_sample_drums": true,
  "render_fx": true,
  "apply_mastering": true
}
```

**Response:**
```json
{
  "status": "success",
  "genre": "HOUSE",
  "sample_drums": true,
  "fx_rendered": true,
  "lufs": -14.2,
  "duration_sec": 67.5
}
```

**Processing Pipeline:**
1. Load genre-specific mix preset
2. Render drums with WAV samples (DrumSampler)
3. Render FX stem (FXPlayer)
4. Render melodic instruments (FluidSynth)
5. Mix stems with MIDI-based sidechain
6. Apply mastering chain

---

## Testing

### Phase 9 Test Script

**File:** `scripts/test_phase9.py`

**What It Does:**
1. Select 3 random images from `ml/data/raw_images/`
2. Generate MIDI with C++ core (genre selection)
3. Render audio with Python pipeline (sample drums, FX, mixing)
4. Save outputs to `output/` folder

**Usage:**
```bash
# Build C++ core first
cd cpp-core
mkdir build && cd build
cmake .. && cmake --build .

# Run test
cd ../..
python scripts/test_phase9.py
```

**Expected Outputs:**
- `output/phase9_test1.mid` - MIDI composition
- `output/phase9_test1.wav` - Final audio (mastered)
- `output/phase9_test2.mid` / `test2.wav`
- `output/phase9_test3.mid` / `test3.wav`

**Validation:**
- Listen to each track
- Verify genre differences (Rap vs House vs R&B)
- Check for sample-based drums (punchy, realistic)
- Verify sidechain pumping (bass ducks on kick)
- Check for FX transitions (uplifters before drops)

---

## File Structure

```
SoundCanvas/
├── cpp-core/
│   ├── include/
│   │   ├── SongSpec.hpp         # ✓ Genre enum, structs
│   │   └── Composer.hpp         # ✓ Genre-aware composition
│   └── src/
│       ├── SongSpec.cpp         # ✓ Genre selection, activity
│       ├── Composer.cpp         # ✓ Swing, patterns, chords
│       └── main.cpp             # ✓ Genre display
│
├── audio-producer/
│   ├── app.py                   # ✓ Updated with Phase 9
│   ├── drum_sampler.py          # ✓ Sample-based drums
│   ├── fx_player.py             # ✓ FX rendering
│   ├── stem_mixer.py            # ✓ MIDI-based sidechain
│   ├── assets/
│   │   ├── kits/
│   │   │   ├── trap_808.yaml    # ✓ Rap drum kit
│   │   │   ├── house.yaml       # ✓ House drum kit
│   │   │   └── rnb_soft.yaml    # ✓ R&B drum kit
│   │   ├── fx/
│   │   │   └── fx_config.yaml   # ✓ FX sample config
│   │   └── samples/             # Downloaded from Freesound
│   │       ├── trap_808/
│   │       ├── house/
│   │       └── rnb_soft/
│   └── mix/
│       ├── schema.py            # ✓ MixPreset dataclasses
│       └── presets/
│           ├── rap.yaml         # ✓ Rap mix settings
│           ├── house.yaml       # ✓ House mix settings
│           └── rnb.yaml         # ✓ R&B mix settings
│
├── tools/
│   └── fetch_freesound_assets.py # ✓ Freesound downloader
│
├── scripts/
│   └── test_phase9.py           # ✓ End-to-end test
│
└── config/
    └── freesound.json           # Freesound API credentials
```

---

## Dependencies

### Python Packages (audio-producer)
```bash
pip install mido soundfile scipy numpy pyyaml requests
```

- `mido` - MIDI file parsing
- `soundfile` - WAV/OGG/FLAC I/O
- `scipy` - Signal processing (filters, resampling)
- `numpy` - Audio arrays
- `pyyaml` - Config file parsing
- `requests` - Freesound API

### System Requirements
- FluidSynth (for melodic instrument rendering)
- CMake + C++ compiler (for cpp-core)

---

## Usage Guide

### 1. Download Drum Samples

```bash
# Set up Freesound API credentials
cp config/env.example config/freesound.json
# Edit freesound.json with your API key

# Download samples
python tools/fetch_freesound_assets.py --kit trap_808
python tools/fetch_freesound_assets.py --kit house
python tools/fetch_freesound_assets.py --kit rnb_soft
python tools/fetch_freesound_assets.py --fx all
```

### 2. Build C++ Core

```bash
cd cpp-core
mkdir build && cd build
cmake ..
cmake --build .
```

### 3. Test End-to-End

```bash
# Test with 3 random images
python scripts/test_phase9.py

# Check outputs
ls output/
# phase9_test1.mid, phase9_test1.wav
# phase9_test2.mid, phase9_test2.wav
# phase9_test3.mid, phase9_test3.wav
```

### 4. Run Production Service (Docker)

```bash
# Build services
docker-compose build

# Start services
docker-compose up

# Test via API
curl -X POST http://localhost:9000/generate \
  -F "image=@test_image.jpg" \
  -F "genre=HOUSE"
```

---

## Genre Characteristics Reference

| Genre | Tempo | Drums | Harmony | Swing | Sidechain | Mix |
|-------|-------|-------|---------|-------|-----------|-----|
| **EDM_CHILL** | 100-115 | Soft kicks, sparse | Ambient pads | None | Light (0.3) | Reverb-heavy |
| **EDM_DROP** | 125-135 | Hard kicks, builds | Power chords | None | Heavy (0.7) | Bright, loud |
| **HOUSE** | 120-128 | Four-on-floor | Major 7ths | None | Medium (0.5) | Pumping bass |
| **RAP** | 80-100 | Trap 808s, sparse | Minor triads | Light (0.2) | Heavy (0.6) | Dry, punchy |
| **RNB** | 90-110 | Soft, syncopated | Jazz chords | Heavy (0.4) | Light (0.3) | Warm, lush |

---

## Known Issues & Future Work

### Current Limitations
1. **Sample Coverage**: Freesound API may not return enough samples (need fallbacks)
2. **FX Timing**: Simple heuristic for FX placement (could use ML-based section detection)
3. **Velocity Layers**: Only 2 layers (soft/hard), could use more for realism
4. **Genre Detection**: Based on image features (could train dedicated genre classifier)

### Future Enhancements
1. **More Genres**: Techno, Dubstep, Indie, Jazz
2. **Custom Samples**: Allow user uploads
3. **Real-time Tweaking**: Adjust mix settings via UI
4. **Multi-language Support**: Non-English genre names
5. **Advanced FX**: Risers with pitch/filter automation

---

## Implementation Notes

### Design Decisions

**Why Sample-Based Drums?**
- GM soundfonts sound unrealistic for modern genres
- Freesound provides authentic, genre-specific sounds
- WAV one-shots allow velocity layers and round-robin

**Why MIDI-Based Sidechain?**
- More precise than audio peak detection
- Can generate envelope before audio rendering
- Allows pre-visualization of ducking effect

**Why YAML Configs?**
- Easy to edit without code changes
- Human-readable
- Version-controllable
- Shareable between users

**Why Freesound API?**
- Free, community-driven
- High-quality samples
- Automated fetching
- Legal/licensed content

### Code Quality

- **Type Hints**: All Python functions have type annotations
- **Error Handling**: Try/except blocks with fallbacks
- **Logging**: Verbose console output for debugging
- **Modularity**: Each component (drums, FX, mixing) is independent
- **Testability**: Test script validates end-to-end pipeline

---

## Credits

**Person A (Composition):**
- Genre system architecture
- Swing timing implementation
- Drum pattern library
- Chord progression generator
- Section activity planner

**Person B (Production):**
- Sample-based drum renderer
- Freesound integration
- Genre-aware mixing system
- MIDI-based sidechain
- FX player with procedural fallbacks
- Pipeline integration

**External Libraries:**
- FluidSynth (MIDI synthesis)
- Freesound.org (sample library)
- Scipy (signal processing)
- Mido (MIDI parsing)

---

## Summary

Phase 9 successfully adds **genre diversity** to SoundCanvas:

✓ **5 distinct genres** with authentic characteristics  
✓ **Sample-based drums** for realistic percussion  
✓ **Genre-aware mixing** with YAML presets  
✓ **MIDI-based sidechain** for precise ducking  
✓ **FX player** with Freesound samples + procedural fallbacks  
✓ **Complete integration** into production pipeline  
✓ **End-to-end testing** with random images  

**Result**: SoundCanvas now generates Rap, House, and R&B tracks that sound distinctly different from each other, with production quality approaching professional EDM standards.

**Next Phase**: Phase 10 could focus on **user controls** (genre selection UI, mix tweaking), **more genres**, or **ML-based section detection** for smarter FX placement.
