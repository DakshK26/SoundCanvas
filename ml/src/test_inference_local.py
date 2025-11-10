from __future__ import annotations
from pathlib import Path
import numpy as np
import tensorflow as tf

MODEL_EXPORT_PATH = Path("models/exported_model")

def main():
    """
    Load the trained SavedModel and test it with sample features.
    This validates the model works before deploying to TF Serving.
    """
    print("Loading model from disk...")
    # Use tf.saved_model.load for exported SavedModel format
    loaded = tf.saved_model.load(str(MODEL_EXPORT_PATH))
    infer = loaded.signatures["serving_default"]
    
    # Create test features: [avgR, avgG, avgB, brightness]
    # Example: bright, slightly blue-ish image
    test_features = np.array([
        [0.8, 0.7, 0.9, 0.8],  # Bright blue-ish
        [0.2, 0.3, 0.1, 0.2],  # Dark image
        [0.9, 0.1, 0.1, 0.4],  # Red-ish
    ], dtype="float32")
    
    print("\nInput features:")
    print(test_features)
    
    # Run inference - need to convert to tensor
    input_tensor = tf.constant(test_features)
    output = infer(input_tensor)
    # Extract the output tensor (key might vary, usually 'output_0' or similar)
    predictions = list(output.values())[0].numpy()
    
    # Display results
    print("\nPredicted music parameters:")
    print("Format: [tempo_bpm, base_frequency, brightness, volume, duration_seconds]")
    for i, pred in enumerate(predictions):
        print(f"Sample {i+1}: {pred}")
    
    # Sanity check ranges
    print("\nSanity checks:")
    print(f"  Tempo range: {predictions[:, 0].min():.1f} - {predictions[:, 0].max():.1f} BPM")
    print(f"  Frequency range: {predictions[:, 1].min():.1f} - {predictions[:, 1].max():.1f} Hz")
    print(f"  Duration range: {predictions[:, 4].min():.1f} - {predictions[:, 4].max():.1f} sec")

if __name__ == "__main__":
    main()