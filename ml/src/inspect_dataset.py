#!/usr/bin/env python3
"""
Sanity-check script for the generated dataset.

Loads dataset.npz and prints:
  - Sample images with their features
  - Generated music parameters
  - Parameter distributions

Usage:
    python -m src.inspect_dataset
"""

from pathlib import Path
import numpy as np
from .pseudo_labels import MusicParameters

# Feature names for pretty printing
FEATURE_NAMES = [
    "avgR", "avgG", "avgB", "brightness",
    "hue", "saturation", "colorfulness", "contrast"
]

# Parameter names for pretty printing
PARAM_NAMES = [
    "tempo_bpm", "base_frequency", "energy", "brightness",
    "reverb", "scale_type", "pattern_type"
]

SCALE_NAMES = ["Major", "Minor", "Dorian", "Lydian"]
PATTERN_NAMES = ["Pad", "Arp", "Chords"]

def load_dataset(path: str | Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Load dataset from .npz file."""
    data = np.load(path)
    return data["X"], data["Y"], data["names"]

def print_sample(idx: int, name: str, features: np.ndarray, params: np.ndarray):
    """Pretty print a single sample."""
    print(f"\n{'='*70}")
    print(f"Sample #{idx}: {name}")
    print(f"{'='*70}")
    
    print("\n📊 VISUAL FEATURES:")
    for i, fname in enumerate(FEATURE_NAMES):
        print(f"  {fname:15s} = {features[i]:6.3f}")
    
    print("\n🎵 MUSIC PARAMETERS:")
    for i, pname in enumerate(PARAM_NAMES):
        val = params[i]
        if pname == "scale_type":
            scale_idx = int(round(val))
            scale_name = SCALE_NAMES[scale_idx] if 0 <= scale_idx < len(SCALE_NAMES) else "Unknown"
            print(f"  {pname:15s} = {val:6.3f} → {scale_name}")
        elif pname == "pattern_type":
            pattern_idx = int(round(val))
            pattern_name = PATTERN_NAMES[pattern_idx] if 0 <= pattern_idx < len(PATTERN_NAMES) else "Unknown"
            print(f"  {pname:15s} = {val:6.3f} → {pattern_name}")
        else:
            print(f"  {pname:15s} = {val:6.3f}")

def print_statistics(X: np.ndarray, Y: np.ndarray):
    """Print dataset statistics."""
    print(f"\n{'='*70}")
    print(f"DATASET STATISTICS")
    print(f"{'='*70}")
    print(f"\nTotal samples: {len(X)}")
    
    print(f"\n📊 FEATURE RANGES:")
    print(f"{'Feature':15s} {'Min':>8s} {'Max':>8s} {'Mean':>8s} {'Std':>8s}")
    print("-" * 55)
    for i, fname in enumerate(FEATURE_NAMES):
        print(f"{fname:15s} {X[:, i].min():8.3f} {X[:, i].max():8.3f} {X[:, i].mean():8.3f} {X[:, i].std():8.3f}")
    
    print(f"\n🎵 PARAMETER RANGES:")
    print(f"{'Parameter':15s} {'Min':>8s} {'Max':>8s} {'Mean':>8s} {'Std':>8s}")
    print("-" * 55)
    for i, pname in enumerate(PARAM_NAMES):
        print(f"{pname:15s} {Y[:, i].min():8.3f} {Y[:, i].max():8.3f} {Y[:, i].mean():8.3f} {Y[:, i].std():8.3f}")
    
    # Distribution of discrete parameters
    scale_types = Y[:, 5].round().astype(int)
    pattern_types = Y[:, 6].round().astype(int)
    
    print(f"\n🎼 SCALE TYPE DISTRIBUTION:")
    for i, name in enumerate(SCALE_NAMES):
        count = (scale_types == i).sum()
        pct = 100.0 * count / len(scale_types) if len(scale_types) > 0 else 0
        print(f"  {name:10s}: {count:4d} ({pct:5.1f}%)")
    
    print(f"\n🎹 PATTERN TYPE DISTRIBUTION:")
    for i, name in enumerate(PATTERN_NAMES):
        count = (pattern_types == i).sum()
        pct = 100.0 * count / len(pattern_types) if len(pattern_types) > 0 else 0
        print(f"  {name:10s}: {count:4d} ({pct:5.1f}%)")

def main():
    """Main inspection routine."""
    dataset_path = Path("data/dataset.npz")
    
    if not dataset_path.exists():
        print(f"❌ Dataset not found at {dataset_path}")
        print("\nRun this first:")
        print("  python -m src.dataset")
        return
    
    X, Y, names = load_dataset(dataset_path)
    
    print(f"\n✅ Loaded dataset from {dataset_path}")
    print(f"   X shape: {X.shape} (features)")
    print(f"   Y shape: {Y.shape} (parameters)")
    
    # Print first 5 samples
    num_samples = min(5, len(X))
    print(f"\n{'='*70}")
    print(f"SHOWING FIRST {num_samples} SAMPLES")
    print(f"{'='*70}")
    
    for i in range(num_samples):
        print_sample(i, names[i], X[i], Y[i])
    
    # Print overall statistics
    print_statistics(X, Y)
    
    print(f"\n{'='*70}")
    print("✅ Sanity check complete!")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    main()
