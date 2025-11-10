"""
Test the trained model locally (Phase 5.5 version).
Tests inference on actual images using the new 8-feature input.
"""
import numpy as np
import tensorflow as tf
from pathlib import Path
import sys
import cv2

# Import model contract
from src.model_contract import INPUT_DIM, OUTPUT_DIM, INPUT_NAMES, OUTPUT_NAMES

def extract_features_from_image(image_path):
    """
    Extract 8 features from an image.
    Matches Person A's feature extraction logic.
    """
    img = cv2.imread(str(image_path))
    if img is None:
        raise ValueError(f"Could not load image: {image_path}")
    
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img_hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
    # Normalize to 0-1
    img_norm = img_rgb / 255.0
    
    # 1-3: Average RGB
    avgR = img_norm[:, :, 0].mean()
    avgG = img_norm[:, :, 1].mean()
    avgB = img_norm[:, :, 2].mean()
    
    # 4: Brightness (luminance)
    brightness = (0.299 * avgR + 0.587 * avgG + 0.114 * avgB)
    
    # 5-6: Hue and Saturation (normalized)
    hue = img_hsv[:, :, 0].mean() / 179.0  # OpenCV hue is 0-179
    saturation = img_hsv[:, :, 1].mean() / 255.0
    
    # 7: Colorfulness (simplified metric)
    rg = img_norm[:, :, 0] - img_norm[:, :, 1]
    yb = 0.5 * (img_norm[:, :, 0] + img_norm[:, :, 1]) - img_norm[:, :, 2]
    colorfulness = np.sqrt(rg.std()**2 + yb.std()**2)
    
    # 8: Contrast (standard deviation of grayscale)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    contrast = gray.std() / 255.0
    
    return np.array([avgR, avgG, avgB, brightness, hue, saturation, colorfulness, contrast], dtype=np.float32)

def test_model():
    """Test the trained model on sample images."""
    model_path = Path(__file__).parent.parent / "models" / "exported_model_versioned" / "1"
    
    if not model_path.exists():
        raise FileNotFoundError(
            f"Model not found at {model_path}.\n"
            "Train the model first: python -m src.train_model"
        )
    
    print("\n🧪 Phase 5.5 Model Inference Test")
    print("="*70)
    
    # Load model using TFSMLayer for Keras 3 compatibility
    print(f"Loading model from {model_path}...")
    model_layer = tf.keras.layers.TFSMLayer(str(model_path), call_endpoint='serve')
    
    print(f"✅ Loaded model from {model_path}")
    print(f"   Input shape:  (?, {INPUT_DIM})")
    print(f"   Output shape: (?, {OUTPUT_DIM})")
    
    # Test on images
    raw_images_dir = Path(__file__).parent.parent / "data" / "raw_images"
    
    if not raw_images_dir.exists():
        print(f"\n❌ No images found at {raw_images_dir}")
        print("Download images first: python -m src.download_images")
        return
    
    test_images = list(raw_images_dir.glob("image_*.jpg"))[:5]
    
    if not test_images:
        print(f"\n❌ No images found in {raw_images_dir}")
        return
    
    print(f"\n🖼️  Testing on {len(test_images)} sample images...")
    print("="*70)
    
    for img_path in test_images:
        print(f"\n📷 Image: {img_path.name}")
        print("-"*70)
        
        # Extract features
        features = extract_features_from_image(str(img_path))
        features_array = np.array([features], dtype=np.float32)  # shape: (1, 8)
        
        # Predict using the model layer
        prediction = model_layer(features_array).numpy()[0]
        
        # Display input features
        print("\n📊 Input Features:")
        for name, val in zip(INPUT_NAMES, features):
            print(f"  {name:15s}: {val:8.3f}")
        
        # Display predictions
        print("\n🎵 Predicted Music Parameters:")
        for name, val in zip(OUTPUT_NAMES, prediction):
            if name in ["scale_type", "pattern_type"]:
                scale_map = {0: "major", 1: "minor", 2: "dorian", 3: "lydian"}
                pattern_map = {0: "pad", 1: "arp", 2: "chords"}
                rounded = int(round(val))
                if name == "scale_type":
                    label = scale_map.get(rounded, "unknown")
                    print(f"  {name:15s}: {val:8.3f} → {rounded} ({label})")
                else:
                    label = pattern_map.get(rounded, "unknown")
                    print(f"  {name:15s}: {val:8.3f} → {rounded} ({label})")
            else:
                print(f"  {name:15s}: {val:8.3f}")
        
        print("-"*70)
    
    print("\n✅ Test complete!")
    print("="*70)
    print("\n🎯 Next steps:")
    print("  1. Start Docker services: cd ../infra && docker-compose up")
    print("  2. Test via HTTP: python -m src.test_inference_serving")
    print("="*70 + "\n")

if __name__ == "__main__":
    test_model()