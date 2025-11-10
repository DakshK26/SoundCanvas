# ml/src/dataset.py
from pathlib import Path
import numpy as np
from .feature_extractor import compute_image_features
from .pseudo_labels import map_features_to_music, music_params_to_vector

def build_dataset_raw_images(image_folder: str | Path, out_path: str | Path) -> None:
    """
    Build training dataset from raw images.
    
    For each image:
        1. Extract 8-dim visual features
        2. Apply rule-based mapping → 7-dim music parameters
        3. Save (features, parameters) pairs
    
    Output dataset.npz contains:
        X: (N, 8) - image features
        Y: (N, 7) - music parameters
        names: (N,) - image filenames
    """
    image_folder = Path(image_folder)
    xs = []
    ys = []
    names = []

    # Support both jpg and png files
    image_paths = list(image_folder.glob("*.jpg")) + list(image_folder.glob("*.png"))
    
    if len(image_paths) == 0:
        print(f"WARNING: No images found in {image_folder}")
        print("Expected .jpg or .png files in ml/data/raw_images/")
        print("Person B should populate this folder with 500-3000 images.")
    
    for img_path in sorted(image_paths):  # Sort for reproducibility
        try:
            feats = compute_image_features(img_path)  # (8,)
            mp = map_features_to_music(feats)
            vec = music_params_to_vector(mp)          # (7,)

            xs.append(feats)
            ys.append(vec)
            names.append(img_path.name)
        except Exception as e:
            print(f"Skipping {img_path.name}: {e}")
            continue

    if len(xs) == 0:
        raise ValueError("No valid images processed. Cannot build dataset.")

    X = np.stack(xs, axis=0)  # shape: (N, 8)
    Y = np.stack(ys, axis=0)  # shape: (N, 7)

    print(f"Dataset built: {len(xs)} images")
    print(f"  X shape: {X.shape} (features)")
    print(f"  Y shape: {Y.shape} (music parameters)")
    print(f"  Feature ranges:")
    print(f"    Min: {X.min(axis=0)}")
    print(f"    Max: {X.max(axis=0)}")
    print(f"  Parameter ranges:")
    print(f"    Min: {Y.min(axis=0)}")
    print(f"    Max: {Y.max(axis=0)}")

    np.savez(out_path, X=X, Y=Y, names=np.array(names))
    print(f"Saved to {out_path}")

if __name__ == "__main__":
    build_dataset_raw_images(
        "data/raw_images",
        "data/dataset.npz",
    )
