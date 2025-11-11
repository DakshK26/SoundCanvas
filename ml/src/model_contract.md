# Model Contract Documentation

## Current State (Phase 6)

### Input Features (X): 8 dimensions
```python
[
    avgR,          # 0-1, average red channel
    avgG,          # 0-1, average green channel
    avgB,          # 0-1, average blue channel
    brightness,    # 0-1, perceived luminance
    hue,           # 0-1, HSV hue (color wheel position)
    saturation,    # 0-1, HSV saturation (color intensity)
    colorfulness,  # 0-1, Hasler & Süsstrunk colorfulness metric
    contrast       # 0-1, grayscale standard deviation
]
```

### Output Parameters (Y): 7 dimensions
```python
[
    tempoBpm,        # 40-90 BPM, rhythm speed
    baseFrequency,   # 100-400 Hz, root note frequency
    energy,          # 0-1, note density/complexity
    brightness,      # 0-1, timbre control (sine↔triangle)
    reverb,          # 0-1, spatial depth (250-400ms delay)
    scaleType,       # 0-3: Major/Minor/Dorian/Lydian (discrete)
    patternType      # 0-2: Pad/Arpeggio/Chords (discrete)
]
```

### Training
- **Dataset**: Generated from `ml/src/dataset.py` using heuristic pseudo-labels
- **Model**: Dense feedforward network (128→128→64→7)
- **Location**: `ml/models/exported_model_versioned/1/`
- **Serving**: TensorFlow Serving REST API at `http://localhost:8501/v1/models/soundcanvas:predict`

---

## Phase 7 Extension (Derived, Not Learned)

### Additional Style Controls
These are **derived in C++** from image features + music parameters, **not predicted by the model**:

```cpp
struct StyleParameters {
    AmbienceType ambienceType;      // 0-4: None/Ocean/Rain/Forest/City
    InstrumentPreset instrumentPreset;  // 0-3: Pad/Keys/Pluck/Bell
    float moodScore;                // 0-1: lushness/pleasantness
};
```

**Derivation Logic** (in `cpp-core/src/MusicalStyle.cpp`):
- `ambienceType`: Based on hue (blue→ocean, green→forest) + brightness/contrast
- `instrumentPreset`: Based on patternType + brightness + energy
- `moodScore`: Weighted combination of saturation, colorfulness, brightness, contrast

**Why Not Learned Yet?**
- No ground truth labels for "ocean" vs "forest" in image dataset
- Heuristic rules provide reasonable behavior without retraining
- Can be promoted to learned parameters later if dataset is expanded with semantic labels

---

## Future Extension (Phase 8+): Expand Model Output

### Option 1: Add Style Controls as Learned Outputs

Extend Y to **9-10 dimensions**:

```python
[
    # Existing (7 dims)
    tempoBpm,
    baseFrequency,
    energy,
    brightness,
    reverb,
    scaleType,
    patternType,
    
    # New learned style controls (2-3 dims)
    ambienceType,      # 0-4: discrete, learned from image semantics
    instrumentPreset,  # 0-3: discrete, learned from visual texture
    moodScore          # 0-1: continuous, learned from aesthetic quality
]
```

**Requirements**:
1. **Dataset Expansion**: Add semantic labels or use pre-trained image embeddings
   - Option A: Manual labeling (ocean/forest/city tags on subset of images)
   - Option B: Use CLIP/vision transformer to classify images into ambience categories
   - Option C: Crowdsource aesthetic ratings for moodScore ground truth

2. **Pseudo-Label Updates** (`ml/src/pseudo_labels.py`):
   ```python
   def map_features_to_music(features):
       # Existing 7 params...
       
       # New: Ambience type from hue + semantic hints
       ambience_type = classify_ambience(features)  # 0-4
       
       # New: Instrument preset from texture/pattern
       instrument_preset = classify_instrument(features)  # 0-3
       
       # New: Mood score from aesthetic quality
       mood_score = compute_mood_score(features)  # 0-1
       
       return MusicParameters(..., ambience_type, instrument_preset, mood_score)
   ```

3. **Model Changes**:
   - Update `INPUT_DIM = 8`, `OUTPUT_DIM = 10` in `train_model.py`
   - Add loss weighting for discrete vs continuous outputs
   - Retrain with expanded dataset

4. **C++ Changes**:
   - Update `ModelClient.cpp` to parse 10-dimensional predictions
   - Replace `deriveStyle()` calls with direct use of model outputs
   - Keep heuristic fallback for backward compatibility

### Option 2: Use Audio Embeddings (Advanced)

Instead of raw parameters, predict **audio embedding vectors** that map to pre-composed instrumental templates:

```python
# Y becomes a high-dimensional embedding (e.g., 128 dims)
Y_embedding = audio_encoder(reference_track)  # Use pre-trained model

# At inference:
image → features → model → embedding → nearest_neighbor(templates) → audio
```

**Requires**:
- Pre-trained audio embedding model (e.g., CLAP, Jukebox, MusicLM)
- Library of reference tracks with known embeddings
- Significant infrastructure changes (embeddings → audio synthesis)

**Recommendation**: Only pursue if quality requirements exceed what parameter-based synthesis can achieve.

---

## Migration Path

### Short-term (Phase 7-8):
✅ Keep 8→7 model as-is  
✅ Use derived style controls in C++  
✅ Gather user feedback on generated audio quality  

### Mid-term (Phase 9-10):
- Collect semantic labels for ~500-1000 images (manual or automated)
- Extend model to 8→10 dimensions
- Retrain with weighted loss for discrete parameters
- A/B test learned vs derived style controls

### Long-term (Phase 11+):
- Integrate pre-trained audio models if quality demands it
- Consider hybrid approach: learned controls + audio embeddings
- Explore fine-tuning on user-curated (image, music) pairs

---

## Implementation Checklist (Phase 8)

When ready to implement learned style controls:

- [ ] Expand dataset with semantic labels or CLIP-based classification
- [ ] Update `ml/src/pseudo_labels.py` with `ambienceType`, `instrumentPreset`, `moodScore` logic
- [ ] Modify `ml/src/dataset.py` to save 10-dimensional Y arrays
- [ ] Update `ml/src/train_model.py`:
  - `OUTPUT_DIM = 10`
  - Add categorical crossentropy for discrete outputs (indices 5-8)
  - Add MSE for continuous outputs (indices 0-4, 9)
- [ ] Retrain model: `python -m src.train_model`
- [ ] Update `cpp-core/src/ModelClient.cpp` to parse 10 predictions
- [ ] Test both model and heuristic modes for backward compatibility
- [ ] Document migration in `PHASE8_SUMMARY.md`

---

## Contact & Notes

**Phase 7 Status**: Style controls derived via heuristics, not learned  
**Model Unchanged**: Still using 8→7 architecture from Phase 6  
**Person B Dependencies**: AudioEngine ready to receive StyleParameters when implemented  

For questions about model architecture or future extensions, see:
- `ml/src/train_model.py` (current training script)
- `cpp-core/src/MusicalStyle.cpp` (derivation logic)
- `PHASE6_SUMMARY.md` (current implementation details)
