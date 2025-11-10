# Phase 5.5: Person A → Person B Handoff

## ✅ Person A Tasks Complete

All Person A responsibilities for Phase 5.5 are **DONE**:

1. ✅ Extended feature extractor (4-dim → 8-dim)
2. ✅ Redesigned MusicParameters (5-dim → 7-dim)
3. ✅ Implemented intelligent rule-based mapping
4. ✅ Updated dataset builder
5. ✅ Created inspection & testing tools

**See `PHASE_5.5_SUMMARY.md` for full technical details.**

---

## 🔄 Person B: Next Steps

### Current State

The ML pipeline now expects:
- **Input**: 8-dim feature vectors from images
- **Output**: 7-dim music parameter vectors
- **Dataset**: `data/dataset.npz` with shapes (N, 8) and (N, 7)

**Currently we only have 2 test images** (both solid red), so the model will overfit badly. Person B needs to acquire real data.

---

## Task 1: Data Acquisition (PRIORITY)

### Goal
Get 500-3000 varied images into `ml/data/raw_images/`

### Options

#### Option A: Unsplash API (Recommended)
```python
# Create ml/src/download_unsplash.py

import requests
from pathlib import Path
import time

ACCESS_KEY = "YOUR_UNSPLASH_ACCESS_KEY"  # Get from unsplash.com/developers
NUM_IMAGES = 1000
OUTPUT_DIR = Path("data/raw_images")

def download_random_images(num_images: int):
    OUTPUT_DIR.mkdir(exist_ok=True, parents=True)
    
    for i in range(num_images):
        response = requests.get(
            "https://api.unsplash.com/photos/random",
            headers={"Authorization": f"Client-ID {ACCESS_KEY}"},
            params={"query": "landscape nature city", "orientation": "landscape"}
        )
        data = response.json()
        img_url = data["urls"]["regular"]
        
        img_data = requests.get(img_url).content
        img_path = OUTPUT_DIR / f"unsplash_{i:04d}.jpg"
        img_path.write_bytes(img_data)
        
        print(f"Downloaded {i+1}/{num_images}: {img_path.name}")
        time.sleep(1)  # Rate limit: ~1 request/sec

if __name__ == "__main__":
    download_random_images(NUM_IMAGES)
```

**Steps**:
1. Sign up at unsplash.com/developers
2. Create an app, get Access Key
3. Run the script: `python -m src.download_unsplash`

#### Option B: Kaggle Dataset
```bash
# Example: Download Places365 subset
kaggle datasets download -d nickj26/places365-standard

# Extract to ml/data/raw_images/
unzip places365-standard.zip -d data/raw_images/

# Or use any "landscape", "scenery", "aesthetic images" dataset
```

#### Option C: Manual Download
Just populate `ml/data/raw_images/` with any 500-3000 `.jpg` or `.png` files from any source.

---

## Task 2: Rebuild Dataset

Once images are in place:

```bash
cd ml
python -m src.dataset
```

**Expected output**:
```
Dataset built: 1000 images
  X shape: (1000, 8) (features)
  Y shape: (1000, 7) (music parameters)
  Feature ranges:
    Min: [...]
    Max: [...]
  Parameter ranges:
    Min: [...]
    Max: [...]
Saved to data/dataset.npz
```

---

## Task 3: Inspect Dataset

Verify the data looks good:

```bash
python -m src.inspect_dataset
```

**Check for**:
- ✅ Varied feature distributions (not all identical)
- ✅ Parameter ranges make musical sense:
  - tempo_bpm: 40-90
  - base_frequency: 100-400
  - energy, brightness, reverb: 0.0-1.0
  - scale_type: mix of 0-3
  - pattern_type: mix of 0-2
- ✅ Bright images → faster tempo, less reverb
- ✅ Dark images → slower tempo, more reverb
- ✅ Blue images → minor scale (1)
- ✅ Red/orange images → major scale (0)

---

## Task 4: Update Model Architecture

Edit `ml/src/train_model.py`:

### Change 1: Update dimensions
```python
# Old:
# INPUT_DIM = 4
# OUTPUT_DIM = 5

# New:
INPUT_DIM = 8   # Changed from 4
OUTPUT_DIM = 7  # Changed from 5
```

### Change 2: Grow network (optional but recommended)
```python
# Old model (too small for 8→7):
# model = tf.keras.Sequential([
#     Dense(32, activation='relu', input_shape=(INPUT_DIM,)),
#     Dense(32, activation='relu'),
#     Dense(OUTPUT_DIM)
# ])

# New model (more capacity):
model = tf.keras.Sequential([
    Dense(64, activation='relu', input_shape=(INPUT_DIM,)),
    Dense(128, activation='relu'),
    Dense(128, activation='relu'),
    Dense(64, activation='relu'),
    Dense(OUTPUT_DIM)
])
```

**Why grow?**: 
- More features (8 vs 4) → more complex patterns to learn
- More outputs (7 vs 5) → more expressive predictions
- More data (1000 vs 2 images) → can support larger model

---

## Task 5: Train Model

```bash
cd ml
python -m src.train_model
```

**Expected behavior**:
- Training loss should decrease over epochs
- With 1000+ images, should see convergence
- Model saved to `models/exported_model/`

**Inspect training**:
```
Epoch 1/50
loss: 123.45 - val_loss: 234.56
Epoch 2/50
loss: 98.76 - val_loss: 187.34
...
```

---

## Task 6: Test Inference Locally

```bash
python -m src.test_inference_local
```

**Check**:
- ✅ Predictions are in expected ranges
- ✅ Different images → different predictions
- ✅ Predictions somewhat match ground truth (within reason)

---

## Task 7: Update TF Serving Container

Edit `ml/serve_model.py` (the Flask app):

### Change 1: Update expected dimensions
```python
# In predict() endpoint:

# Validate input shape
if instances.shape[1] != 8:  # Changed from 4
    return {"error": f"Expected 8 features, got {instances.shape[1]}"}, 400

# ... model prediction ...

# Validate output shape
if predictions.shape[1] != 7:  # Changed from 5
    return {"error": f"Model returned {predictions.shape[1]} outputs, expected 7"}, 500
```

### Change 2: Rebuild Docker image
```bash
cd ml
docker build -f Dockerfile.tfserving -t soundcanvas-tfserving:latest .
```

### Change 3: Test the serving API
```bash
# Start container
docker run -p 8501:8501 soundcanvas-tfserving:latest

# In another terminal, test
python -m src.test_inference_serving
```

---

## Task 8: Manual Listening Tests (Later)

**After C++ integration is updated**, test end-to-end:

1. Run several diverse images through the system
2. Listen to generated audio
3. Verify mappings feel coherent:
   - Sunset (red/orange) → warm major tones, higher freq
   - Ocean (blue) → cool minor tones, lower freq, more reverb
   - Forest (green) → lydian scale, balanced energy
   - Night scene (dark) → slow tempo, heavy reverb

If mapping doesn't feel right, iterate on `pseudo_labels.py` rules and retrain.

---

## Summary Checklist for Person B

- [ ] **Data Acquisition**: Get 500-3000 images into `data/raw_images/`
- [ ] **Rebuild Dataset**: Run `python -m src.dataset`
- [ ] **Inspect**: Run `python -m src.inspect_dataset` and verify distributions
- [ ] **Update Model**: Change `INPUT_DIM=8`, `OUTPUT_DIM=7` in `train_model.py`
- [ ] **Grow Network**: Increase model capacity (32→64→128 units)
- [ ] **Train**: Run `python -m src.train_model` on full dataset
- [ ] **Test Local**: Run `python -m src.test_inference_local`
- [ ] **Update Serving**: Modify `serve_model.py` for 8→7 dimensions
- [ ] **Rebuild Docker**: `docker build -f Dockerfile.tfserving ...`
- [ ] **Test Serving**: Run `python -m src.test_inference_serving`

---

## Questions? Contact Person A

If anything is unclear or broken:

1. Check `PHASE_5.5_SUMMARY.md` for technical details
2. Run `python -m src.test_features` to verify feature extraction
3. Run `python -m src.inspect_dataset` to debug dataset issues
4. Check dataset shapes: `X.shape == (N, 8)` and `Y.shape == (N, 7)`

---

## What's Next? (Phase 6+)

After Person B completes ML training:

### Phase 6: C++ Integration Updates
- Update `ImageFeatures` struct to 8 fields
- Update `ModelClient::predict()` to send 8-dim vectors
- Update `AudioEngine` to interpret 7-dim outputs:
  - Add scale selection (major/minor/dorian/lydian)
  - Add pattern types (pad/arp/chords)
  - Add reverb effect

### Phase 7: Frontend
- React app with GraphQL client
- Image upload + audio playback
- History view with parameter visualization

---

**Good luck, Person B! The foundation is solid. 🚀**
