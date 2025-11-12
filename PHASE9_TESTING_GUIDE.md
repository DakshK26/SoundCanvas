# Phase 9 - Person A Testing Guide

## Quick Start

### 1. Build the Code
```bash
cd c:\Users\khann\OneDrive\Documents\GitHub\SoundCanvas\cpp-core\build
cmake ..
make -j4
```

### 2. Test Genre Variety

#### House Genre (Bright, Saturated Images)
```bash
# Look for images with lots of bright colors, neon, party vibes
./soundcanvas_core --compose-only ../ml/data/raw_images/image_00100.jpg test_house.mid
```
**Expected**:
- Genre: House
- Tempo: 118-132 BPM
- Groove: Driving (swing: 0%)
- Four-on-floor kick pattern
- Off-beat hi-hats
- Uplifting chord progressions

#### Rap/Trap Genre (Dark, High Contrast)
```bash
# Look for urban, gritty, high-contrast images
./soundcanvas_core --compose-only ../ml/data/raw_images/image_00500.jpg test_rap.mid
```
**Expected**:
- Genre: Rap
- Tempo: 70-100 BPM
- Groove: Straight (swing: 15%)
- Syncopated kick pattern
- Ghost snares
- Minimal chord progressions

#### R&B Genre (Warm, Saturated, Soft)
```bash
# Look for warm sunset, smooth, colorful but soft images
./soundcanvas_core --compose-only ../ml/data/raw_images/image_01000.jpg test_rnb.mid
```
**Expected**:
- Genre: R&B
- Tempo: 70-95 BPM
- Groove: Straight (swing: 20%)
- Smooth drum patterns
- Extended chord voicings (7ths, 9ths)
- Bridge sections

#### EDM Drop (High Energy)
```bash
# Look for very vibrant, energetic images
./soundcanvas_core --compose-only ../ml/data/raw_images/image_01500.jpg test_edm_drop.mid
```
**Expected**:
- Genre: EDM Drop
- Tempo: 100-140 BPM
- Groove: Driving (swing: 0%)
- Big drop sections
- Original EDM patterns

#### EDM Chill (Low Energy)
```bash
# Look for calm, muted, ambient images
./soundcanvas_core --compose-only ../ml/data/raw_images/image_02000.jpg test_edm_chill.mid
```
**Expected**:
- Genre: EDM Chill
- Tempo: 80-110 BPM
- Groove: Chill or Straight
- Atmospheric arrangements

### 3. Verify in DAW

Load the MIDI files in your DAW (FL Studio, Ableton, Logic, etc.) and check:

#### Musical Differences
- [ ] House has tight 4-on-floor kick
- [ ] Rap has swung hi-hats (sounds loose/groovy)
- [ ] R&B has ghost snares and smooth feel
- [ ] Chord complexity varies by genre
- [ ] Section structures differ by genre

#### Swing Detection
- [ ] Rap: Hi-hats slightly delayed on off-beats
- [ ] R&B: Even more swing (20% vs 15%)
- [ ] House/EDM: No swing, perfectly quantized

#### Arrangement Variety
- [ ] House: Gradual build, drums enter later
- [ ] Rap: Sparse intro, focused on verse/hook
- [ ] R&B: Smooth transitions, bridge sections
- [ ] Different track activity per section

### 4. Console Output Verification

Check that the console shows:
```
Song Specification:
  Genre: [House|Rap|R&B|EDM Drop|EDM Chill]
  Tempo: [appropriate range] BPM
  Groove: [Driving|Straight|Chill] (swing: [0|15|20]%)
  Sections: [genre-appropriate structure]
```

### 5. Batch Testing Script

```bash
# Test multiple images and compare genres
cd c:\Users\khann\OneDrive\Documents\GitHub\SoundCanvas\cpp-core\build

for i in 00100 00500 01000 01500 02000; do
    echo "=== Testing image_$i.jpg ==="
    ./soundcanvas_core --compose-only \
        ../ml/data/raw_images/image_$i.jpg \
        test_$i.mid
    echo ""
done
```

### 6. What to Look For

#### Genre Classification
Images should map to appropriate genres:
- Bright neon → House
- Dark urban → Rap
- Warm sunset → R&B
- High energy → EDM Drop
- Muted calm → EDM Chill

#### Musical Characteristics

**House**:
- ✅ Kick on every beat (1, 2, 3, 4)
- ✅ Snare on 2 & 4
- ✅ Off-beat hats
- ✅ No swing
- ✅ Big drop sections

**Rap**:
- ✅ Syncopated kicks
- ✅ Ghost snares
- ✅ 15% swing feel
- ✅ Simple progressions (2-4 chords)
- ✅ Verse/hook structure

**R&B**:
- ✅ Smooth, grooving drums
- ✅ 20% swing (most pronounced)
- ✅ Extended chords (7ths, 9ths)
- ✅ Pre-chorus and bridge
- ✅ Warmer, fuller sound

**EDM**:
- ✅ Original behavior maintained
- ✅ Section-based energy
- ✅ Build/drop/break structure

### 7. Common Issues & Troubleshooting

#### Issue: All genres sound the same
**Check**:
- Are you using images with varied characteristics?
- Does console show different genres being selected?
- Try forcing specific image types (bright vs dark vs warm)

#### Issue: Compilation errors
**Check**:
- Did you update all include files?
- Is `#include <algorithm>` present in SongSpec.cpp?
- Run `cmake .. && make clean && make`

#### Issue: No swing detected
**Check**:
- Load MIDI in piano roll view
- Zoom in on hi-hat off-beats
- Compare Rap/R&B (swing) vs House/EDM (no swing)
- Off-beats should be delayed by 10-20 ticks

#### Issue: Wrong genre selected
**Tune** genre selection thresholds in `pickGenre()`:
- Adjust saturation/brightness/contrast thresholds
- Modify tempo range checks
- Add debug output to see why genre was chosen

### 8. Expected Test Results

Run test on 10 random images:
```bash
# Should see variety in output:
- 2-3 House tracks (if images are bright)
- 1-2 Rap tracks (if images are dark/contrasty)
- 1-2 R&B tracks (if images are warm/smooth)
- 3-4 EDM tracks (mixed characteristics)
```

If all 10 are the same genre, genre selection logic needs tuning!

### 9. Performance Benchmarks

Expected generation times:
- Genre selection: <1ms
- Pattern generation: <5ms per bar
- Swing application: <1ms overhead
- Total composition: 100-200ms (same as before)

### 10. Next Steps

Once Person A implementation is verified:
1. ✅ Genres are correctly identified
2. ✅ Musical differences are audible
3. ✅ Swing is working correctly
4. ✅ Arrangements vary by genre

**Then**: Ready for Person B to implement:
- Genre-specific drum kits
- Mix presets (EQ, compression, reverb)
- Sidechain compression
- FX samples (sweeps, impacts)
- Per-genre mastering

---

## Debug Commands

### Enable Verbose Output
Add to code temporarily:
```cpp
std::cout << "[DEBUG] Genre: " << genreName(profile.genre) << "\n";
std::cout << "[DEBUG] Image: sat=" << f.saturation 
          << " bright=" << f.brightness 
          << " contrast=" << f.contrast << "\n";
```

### Test Specific Genre
Force genre selection in code:
```cpp
// In makeSongSpec(), add:
spec.genreProfile = pickGenre(f, m);
// spec.genreProfile.genre = Genre::HOUSE; // Force for testing
```

### Check Swing Amount
Add output in `generateDrumsBarGenre()`:
```cpp
std::cout << "[SWING] Applied " << genre.swingAmount 
          << " to " << genre.name << " drums\n";
```

---

## Success Criteria

✅ **Genre Variety**: 3+ different genres in 10 random images
✅ **Swing Working**: Audible difference in Rap/R&B vs House/EDM
✅ **Drum Patterns**: House 4-on-floor, Rap syncopated, R&B smooth
✅ **Chord Progressions**: Different progressions per genre
✅ **Arrangements**: Section structures vary by genre
✅ **No Regression**: EDM genres still work as before
✅ **Performance**: <200ms composition time

---

**Status**: Ready for testing! 🎵
