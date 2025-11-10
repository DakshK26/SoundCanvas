#!/usr/bin/env python3
"""
Quick test to verify the feature extractor with the existing test images.

This helps validate that the new 8-dim features are being extracted correctly.
"""

from pathlib import Path
import sys
from src.feature_extractor import compute_image_features
from src.pseudo_labels import map_features_to_music, music_params_to_vector

def test_image(img_path: Path):
    """Test feature extraction on a single image."""
    print(f"\n{'='*70}")
    print(f"Testing: {img_path.name}")
    print(f"{'='*70}")
    
    try:
        # Extract features
        features = compute_image_features(img_path)
        print(f"\n✅ Features extracted: {features.shape}")
        print(f"   Values: {features}")
        
        # Generate music parameters
        music_params = map_features_to_music(features)
        print(f"\n✅ Music parameters generated:")
        print(f"   tempo_bpm:      {music_params.tempo_bpm:.2f}")
        print(f"   base_frequency: {music_params.base_frequency:.2f} Hz")
        print(f"   energy:         {music_params.energy:.3f}")
        print(f"   brightness:     {music_params.brightness:.3f}")
        print(f"   reverb:         {music_params.reverb:.3f}")
        print(f"   scale_type:     {music_params.scale_type} ({'Major' if music_params.scale_type == 0 else 'Minor' if music_params.scale_type == 1 else 'Dorian' if music_params.scale_type == 2 else 'Lydian'})")
        print(f"   pattern_type:   {music_params.pattern_type} ({'Pad' if music_params.pattern_type == 0 else 'Arp' if music_params.pattern_type == 1 else 'Chords'})")
        
        # Convert to vector
        param_vector = music_params_to_vector(music_params)
        print(f"\n✅ Parameter vector: {param_vector.shape}")
        print(f"   Values: {param_vector}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Test all images in raw_images folder."""
    raw_images = Path("data/raw_images")
    
    if not raw_images.exists():
        print(f"❌ Folder not found: {raw_images}")
        sys.exit(1)
    
    images = list(raw_images.glob("*.png")) + list(raw_images.glob("*.jpg"))
    
    if len(images) == 0:
        print(f"❌ No images found in {raw_images}")
        sys.exit(1)
    
    print(f"\n{'='*70}")
    print(f"FEATURE EXTRACTOR TEST")
    print(f"{'='*70}")
    print(f"\nFound {len(images)} images in {raw_images}")
    
    for img_path in sorted(images):
        test_image(img_path)
    
    print(f"\n{'='*70}")
    print("✅ All tests complete!")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    main()
