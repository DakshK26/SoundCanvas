# SoundCanvas ML

TensorFlow code to map image features to music parameters.

## 📦 Phase 5.5 Status: ✅ PERSON A COMPLETE

### What's Done (Person A)
- ✅ 8-dim feature extraction (RGB, brightness, HSV, colorfulness, contrast)
- ✅ 7-dim music parameters (tempo, freq, energy, brightness, reverb, scale, pattern)
- ✅ Intelligent rule-based mapping (brightness→tempo+reverb, hue→scale, etc.)
- ✅ Dataset builder updated (8→7 dimensions)
- ✅ Inspection & testing tools

### What's Next (Person B)
- ⏳ Data acquisition: Get 500-3000 images into `data/raw_images/`
- ⏳ Update model dimensions in `train_model.py` (8→7)
- ⏳ Train model on full dataset
- ⏳ Update TF Serving for new dimensions

**See `PERSON_B_TASKS.md` for detailed step-by-step instructions.**

---

## Structure

```
ml/
├── src/                          # Python source code
│   ├── feature_extractor.py      # Extract 8-dim features from images
│   ├── pseudo_labels.py          # Map features → 7-dim music parameters
│   ├── dataset.py                # Build training dataset
│   ├── train_model.py            # Train TensorFlow model
│   ├── test_inference_local.py   # Test model locally
│   ├── test_inference_serving.py # Test TF Serving API
│   ├── inspect_dataset.py        # Dataset sanity-check tool
│   └── test_features.py          # Feature extraction test
├── data/                          # Data files
│   ├── raw_images/               # Input images (Person B to populate!)
│   └── dataset.npz               # Processed dataset (X: 8-dim, Y: 7-dim)
├── models/                        # Exported models
│   └── exported_model/           # TensorFlow SavedModel for serving
├── PHASE_5.5_SUMMARY.md          # Complete technical documentation
├── PERSON_B_TASKS.md             # Step-by-step guide for Person B
└── README.md                      # This file
```

---

## Quick Start (For Person B)

### 1. Data Acquisition
```bash
# Option A: Unsplash (see PERSON_B_TASKS.md for script)
python -m src.download_unsplash

# Option B: Manual download
# Just add 500-3000 .jpg or .png files to data/raw_images/
```

### 2. Build Dataset
```bash
python -m src.dataset
# Expected output: (N, 8) features → (N, 7) parameters
```

### 3. Inspect Dataset
```bash
python -m src.inspect_dataset
# Verify parameter distributions and musical coherence
```

### 4. Update & Train Model
```bash
# Edit src/train_model.py:
# - INPUT_DIM = 8
# - OUTPUT_DIM = 7
# - Grow network to 64-128 units

python -m src.train_model
```

### 5. Test
```bash
python -m src.test_inference_local
python -m src.test_inference_serving  # After starting Flask server
```

---

## Feature Specifications

### Input Features (8-dim)
| Index | Name | Range | Description |
|-------|------|-------|-------------|
| 0 | avgR | 0-1 | Average red channel |
| 1 | avgG | 0-1 | Average green channel |
| 2 | avgB | 0-1 | Average blue channel |
| 3 | brightness | 0-1 | Luminance |
| 4 | hue | 0-1 | HSV hue |
| 5 | saturation | 0-1 | HSV saturation |
| 6 | colorfulness | 0-1 | Color intensity metric |
| 7 | contrast | 0-1 | Grayscale std dev |

### Output Parameters (7-dim)
| Index | Name | Range | Description |
|-------|------|-------|-------------|
| 0 | tempo_bpm | 40-90 | BPM (slow ambient) |
| 1 | base_frequency | 100-400 Hz | Root frequency |
| 2 | energy | 0-1 | Texture density |
| 3 | brightness | 0-1 | Timbre brightness |
| 4 | reverb | 0-1 | Reverb amount |
| 5 | scale_type | 0-3 | 0=Major, 1=Minor, 2=Dorian, 3=Lydian |
| 6 | pattern_type | 0-2 | 0=Pad, 1=Arp, 2=Chords |

---

## Mapping Philosophy

| Visual Feature | → | Music Parameter | Logic |
|----------------|---|-----------------|-------|
| Brightness | → | tempo + reverb | Dark = slow+reverb, Bright = fast+dry |
| Hue | → | scale_type | Blue→Minor, Red→Major, Green→Lydian |
| Saturation | → | energy + pattern | Vivid = busy, Muted = simple |
| Warmth (R-B) | → | base_frequency | Cool = low, Warm = high |

**Design**: All parameters constrained to musically pleasant ranges. Model cannot generate noise.

---

## Documentation

- **`PHASE_5.5_SUMMARY.md`** - Complete technical details of changes
- **`PERSON_B_TASKS.md`** - Step-by-step guide for next steps
- **Code comments** - Inline documentation in all source files

---

## Testing

```bash
# Test feature extraction
python -m src.test_features

# Build dataset (currently 2 test images)
python -m src.dataset

# Inspect dataset
python -m src.inspect_dataset
```

---

**Status**: ✅ Person A complete | ⏳ Person B next

**Current Blocker**: Need 500-3000 images in `data/raw_images/`
