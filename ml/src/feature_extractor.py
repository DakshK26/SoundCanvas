# ml/src/feature_extractor.py
from pathlib import Path
from typing import Tuple
import numpy as np
from PIL import Image

def compute_image_features(path: str | Path) -> np.ndarray:
    img = Image.open(path).convert("RGB")
    arr = np.asarray(img, dtype=np.float32) / 255.0  # H x W x 3 in [0,1]
    avg = arr.mean(axis=(0, 1))  # shape: (3,)
    avg_r, avg_g, avg_b = avg.tolist()
    brightness = float(avg.mean())
    return np.array([avg_r, avg_g, avg_b, brightness], dtype=np.float32)

def compute_features_for_folder(folder: str | Path) -> dict[str, np.ndarray]:
    folder = Path(folder)
    features = {}
    for img_path in folder.glob("*.jpg"):
        features[img_path.name] = compute_image_features(img_path)
    return features
