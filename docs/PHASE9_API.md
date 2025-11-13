# Phase 9 API Reference

Quick reference for using the Phase 9 enhanced audio production API.

---

## Audio Producer Service (Enhanced)

**Base URL**: `http://localhost:9001`

### POST /produce

Enhanced endpoint with Phase 9 features.

#### Request

```json
{
  "midi_path": "/data/composition.mid",
  "output_path": "/data/output/song.wav",
  "genre": "HOUSE",
  "use_sample_drums": true,
  "render_fx": true,
  "apply_mastering": true
}
```

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `midi_path` | string | Yes | - | Path to MIDI file |
| `output_path` | string | Yes | - | Output WAV path |
| `genre` | string | No | "EDM_DROP" | Genre (EDM_CHILL, EDM_DROP, HOUSE, RAP, RNB) |
| `use_sample_drums` | boolean | No | true | Use sample-based drums (Phase 9) |
| `render_fx` | boolean | No | true | Render FX stem (Phase 9) |
| `apply_mastering` | boolean | No | true | Apply mastering chain |

#### Response (Success)

```json
{
  "status": "success",
  "output_path": "/data/output/song.wav",
  "file_size": 5242880,
  "lufs": -14.2,
  "duration_sec": 67.5,
  "stems_count": 3,
  "genre": "HOUSE",
  "sample_drums": true,
  "fx_rendered": true,
  "mastering_applied": true
}
```

#### Response (Error)

```json
{
  "status": "error",
  "message": "MIDI file not found: /data/composition.mid"
}
```

---

## Python API (Direct Usage)

### DrumSampler

```python
from drum_sampler import DrumSampler

sampler = DrumSampler(
    kits_dir='assets/kits',
    samples_dir='assets/samples'
)

# Render MIDI with genre-specific kit
sampler.render_midi(
    midi_path='composition.mid',
    output_path='drums.wav',
    kit_name='trap_808'  # or 'house', 'rnb_soft'
)
```

**Available Kits:**
- `trap_808` - Rap/Trap style (heavy 808s, crisp snares)
- `house` - House style (punchy kicks, sharp hats)
- `rnb_soft` - R&B style (soft kicks, smooth snares)

### FXPlayer

```python
from fx_player import FXPlayer

player = FXPlayer(
    fx_config_path='assets/fx/fx_config.yaml',
    assets_dir='assets'
)

# Render FX stem
player.render_fx_stem(
    midi_path='composition.mid',
    output_path='fx.wav',
    total_duration=120.0,
    fx_events=[
        {'time': 30.0, 'type': 'uplifter', 'duration': 2.0},
        {'time': 60.0, 'type': 'impact', 'duration': 0.5}
    ]
)

# Generate procedural FX
uplifter = player.generate_uplifter(duration=2.0)
downlifter = player.generate_downlifter(duration=1.5)
impact = player.generate_impact(duration=0.5)
```

### MixPreset

```python
from mix.schema import load_mix_preset, get_preset_for_genre

# Load specific preset
preset = load_mix_preset('mix/presets/house.yaml')

print(f"Sidechain amount: {preset.master.sidechain_amount}")
print(f"Reverb wet: {preset.master.reverb_wet}")

# Get preset for genre
preset = get_preset_for_genre('RAP', 'mix/presets/')
```

### Stem Mixer (Enhanced)

```python
from stem_mixer import mix_stems

stems = {
    'drums': 'drums.wav',
    'melodic': 'melodic.wav',
    'fx': 'fx.wav'
}

mix_stems(
    stems=stems,
    output_path='mixed.wav',
    apply_sidechain_to=['melodic'],
    stem_gains={'drums': 1.0, 'melodic': 0.7, 'fx': 0.3},
    midi_path='composition.mid',  # Phase 9: MIDI-based sidechain
    sidechain_amount=0.5
)
```

---

## CLI Tools

### Fetch Freesound Assets

```bash
# Download specific drum kit
python tools/fetch_freesound_assets.py --kit trap_808

# Download all FX samples
python tools/fetch_freesound_assets.py --fx all

# Download specific FX type
python tools/fetch_freesound_assets.py --fx uplifters

# Specify output directory
python tools/fetch_freesound_assets.py --kit house --output assets/samples/
```

### Test Phase 9

```bash
# Test with 3 random images
python scripts/test_phase9.py

# Expected output files:
# output/phase9_test1.mid, output/phase9_test1.wav
# output/phase9_test2.mid, output/phase9_test2.wav
# output/phase9_test3.mid, output/phase9_test3.wav
```

---

## C++ Core (Genre Selection)

The C++ core automatically selects genre based on image features. You can see the selected genre in the console output:

```
Image Analysis:
  Brightness: 0.65
  Saturation: 0.42
  Energy: 0.78

Genre: HOUSE
Tempo: 124 BPM
Key: C Major

Composition complete!
MIDI saved: output/composition.mid
```

**Genre Selection Algorithm:**
- High energy + high brightness → EDM_DROP
- Low energy + high saturation → EDM_CHILL
- Mid energy + balanced colors → HOUSE
- Low brightness + low saturation → RAP
- High saturation + warm colors → RNB

---

## Example Usage (Full Pipeline)

### 1. Command Line

```bash
# Step 1: Generate MIDI from image
./cpp-core/build/soundcanvas image.jpg composition.mid

# Step 2: Render audio with Phase 9
curl -X POST http://localhost:9001/produce \
  -H "Content-Type: application/json" \
  -d '{
    "midi_path": "composition.mid",
    "output_path": "output.wav",
    "genre": "HOUSE",
    "use_sample_drums": true,
    "render_fx": true,
    "apply_mastering": true
  }'
```

### 2. Python Script

```python
import subprocess
import requests
import json

# Generate MIDI
subprocess.run([
    './cpp-core/build/soundcanvas',
    'image.jpg',
    'composition.mid'
])

# Render audio
response = requests.post('http://localhost:9001/produce', json={
    'midi_path': 'composition.mid',
    'output_path': 'output.wav',
    'genre': 'HOUSE',
    'use_sample_drums': True,
    'render_fx': True,
    'apply_mastering': True
})

result = response.json()
print(f"✓ Audio rendered: {result['output_path']}")
print(f"  LUFS: {result['lufs']}")
print(f"  Duration: {result['duration_sec']}s")
print(f"  Genre: {result['genre']}")
```

### 3. Direct Python API

```python
from drum_sampler import DrumSampler
from fx_player import FXPlayer
from mix.schema import get_preset_for_genre
from stem_mixer import mix_stems
from mastering import apply_mastering_chain

# Initialize components
sampler = DrumSampler(kits_dir='assets/kits', samples_dir='assets/samples')
fx_player = FXPlayer(fx_config_path='assets/fx/fx_config.yaml', assets_dir='assets')
preset = get_preset_for_genre('HOUSE', 'mix/presets/')

# Render stems
sampler.render_midi('composition.mid', 'drums.wav', kit_name='house')
fx_player.render_fx_stem('composition.mid', 'fx.wav', total_duration=120.0)

# Mix
stems = {'drums': 'drums.wav', 'fx': 'fx.wav'}
mix_stems(stems, 'mixed.wav', midi_path='composition.mid', 
          sidechain_amount=preset.master.sidechain_amount)

# Master
apply_mastering_chain('mixed.wav', 'final.wav', target_lufs=-14.0)
```

---

## Configuration Files

### Drum Kit Config (YAML)

```yaml
# assets/kits/trap_808.yaml
kit_name: "Trap 808 Kit"
description: "Heavy 808 kicks and crisp snares for trap/rap"

freesound_tags:
  - "808 kick"
  - "trap snare"
  - "hi-hat electronic"

samples:
  36:  # Kick
    freesound_tags: ["808 kick", "bass drum heavy"]
    velocity_layers:
      0-80: "soft"
      81-127: "hard"
  
  38:  # Snare
    freesound_tags: ["trap snare", "snare clap"]
    selection_mode: "round_robin"
```

### Mix Preset (YAML)

```yaml
# mix/presets/house.yaml
buses:
  drums:
    gain: 1.0
    eq_low_boost: 2.0
    eq_high_boost: 2.0
    compression:
      threshold: -10.0
      ratio: 4.0
  
  melodic:
    gain: 0.7
    reverb_wet: 0.15
    compression:
      threshold: -12.0
      ratio: 3.0

master:
  sidechain_amount: 0.5
  reverb_wet: 0.1
  limiter_threshold: -1.0
```

---

## Error Handling

### Common Errors

**"Import 'mido' could not be resolved"**
```bash
pip install mido soundfile pyyaml requests
```

**"Drum kit not found: trap_808"**
```bash
python tools/fetch_freesound_assets.py --kit trap_808
```

**"MIDI file not found"**
- Ensure C++ core ran successfully
- Check MIDI path in request

**"FluidSynth error"**
- Install FluidSynth (`choco install fluidsynth` on Windows)
- Verify soundfont path

---

## Performance

**Typical Rendering Times** (on modern hardware):
- MIDI generation (C++): 0.5-2 seconds
- Drum rendering (samples): 1-3 seconds
- FX rendering: 0.5-1 second
- Mixing: 2-4 seconds
- Mastering: 1-2 seconds
- **Total**: 5-12 seconds for a 60-second track

**Optimizations:**
- Use `use_sample_drums=false` for faster rendering (FluidSynth only)
- Set `render_fx=false` to skip FX stem
- Disable mastering for quick previews

---

## Supported Audio Formats

**Input (MIDI):**
- `.mid` (MIDI Type 0/1)

**Output (Audio):**
- `.wav` (44100 Hz, 16-bit, stereo)

**Sample Formats:**
- `.wav` (preferred)
- `.ogg` (Freesound downloads)
- `.flac` (high quality)

---

## Version Info

**Phase 9 Version**: 1.0.0  
**API Version**: 2.0 (backward compatible)  
**Python**: 3.8+  
**C++**: C++17  

---

**For detailed documentation, see:**
- `docs/PHASE9_COMPLETE.md` - Full implementation details
- `docs/PHASE9_SETUP.md` - Setup instructions
- `docs/PHASE9_SUMMARY.md` - High-level overview
