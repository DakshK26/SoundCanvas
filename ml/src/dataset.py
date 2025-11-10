# ml/src/dataset.py
from pathlib import Path
import numpy as np
from .feature_extractor import compute_image_features
from .pseudo_labels import map_features_to_music, music_params_to_vector

def build_dataset_raw_images(image_folder: str | Path, out_path: str | Path) -> None:
    image_folder = Path(image_folder)
    xs = []
    ys = []
    names = []

    # Support both jpg and png files
    image_paths = list(image_folder.glob("*.jpg")) + list(image_folder.glob("*.png"))
    
    for img_path in image_paths:
        feats = compute_image_features(img_path)
        mp = map_features_to_music(feats)
        vec = music_params_to_vector(mp)

        xs.append(feats)
        ys.append(vec)
        names.append(img_path.name)

    X = np.stack(xs, axis=0)  # shape: (N, 4)
    Y = np.stack(ys, axis=0)  # shape: (N, 5)

    np.savez(out_path, X=X, Y=Y, names=np.array(names))

if __name__ == "__main__":
    build_dataset_raw_images(
        "data/raw_images",
        "data/dataset.npz",
    )
