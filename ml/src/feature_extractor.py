# ml/src/feature_extractor.py
from pathlib import Path
from typing import Tuple
import numpy as np
from PIL import Image

def compute_image_features(path: str | Path) -> np.ndarray:
    """
    Extract 8 visual features from an image:
    [avgR, avgG, avgB, brightness, hue, saturation, colorfulness, contrast]
    
    Returns:
        np.ndarray of shape (8,) with values normalized appropriately
    """
    img = Image.open(path).convert("RGB")
    arr = np.asarray(img, dtype=np.float32) / 255.0  # H x W x 3 in [0,1]
    
    # Basic RGB features
    avg = arr.mean(axis=(0, 1))  # shape: (3,)
    avg_r, avg_g, avg_b = avg.tolist()
    brightness = float(avg.mean())
    
    # HSV features for hue and saturation
    hsv_img = Image.open(path).convert("RGB").convert("HSV")
    hsv_arr = np.asarray(hsv_img, dtype=np.float32)
    
    # Hue: normalized to [0, 1] (HSV hue is 0-360 in PIL, stored as 0-255)
    hue_channel = hsv_arr[:, :, 0] / 255.0  # Now [0, 1]
    hue = float(hue_channel.mean())
    
    # Saturation: normalized to [0, 1]
    sat_channel = hsv_arr[:, :, 1] / 255.0
    saturation = float(sat_channel.mean())
    
    # Colorfulness metric (Hasler and Süsstrunk 2003)
    # Based on rg and yb opponent color space
    R = arr[:, :, 0]
    G = arr[:, :, 1]
    B = arr[:, :, 2]
    
    rg = R - G
    yb = 0.5 * (R + G) - B
    
    std_rg = np.std(rg)
    std_yb = np.std(yb)
    mean_rg = np.mean(rg)
    mean_yb = np.mean(yb)
    
    colorfulness = float(np.sqrt(std_rg**2 + std_yb**2) + 0.3 * np.sqrt(mean_rg**2 + mean_yb**2))
    # Normalize colorfulness (typical range is 0-100, we'll clamp to [0, 1])
    colorfulness = min(colorfulness / 100.0, 1.0)
    
    # Contrast: standard deviation of grayscale intensity
    gray = 0.299 * R + 0.587 * G + 0.114 * B
    contrast = float(np.std(gray))  # Already in [0, 1] range due to normalization
    
    return np.array(
        [avg_r, avg_g, avg_b, brightness, hue, saturation, colorfulness, contrast],
        dtype=np.float32
    )

def compute_features_for_folder(folder: str | Path) -> dict[str, np.ndarray]:
    folder = Path(folder)
    features = {}
    for img_path in folder.glob("*.jpg"):
        features[img_path.name] = compute_image_features(img_path)
    return features
