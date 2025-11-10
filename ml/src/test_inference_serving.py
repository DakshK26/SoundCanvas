from __future__ import annotations
import requests
import numpy as np

# TF Serving REST API endpoint
TF_SERVING_URL = "http://localhost:8501/v1/models/soundcanvas:predict"

def main():
    """
    Test TensorFlow Serving by sending requests to the REST API.
    This validates the model is properly deployed and accessible.
    """
    print("Testing TensorFlow Serving REST API...")
    print(f"Endpoint: {TF_SERVING_URL}\n")
    
    # Create test features: [avgR, avgG, avgB, brightness]
    test_features = np.array([
        [0.8, 0.7, 0.9, 0.8],  # Bright blue-ish
        [0.2, 0.3, 0.1, 0.2],  # Dark image
        [0.9, 0.1, 0.1, 0.4],  # Red-ish
    ], dtype="float32")
    
    # TF Serving expects {"instances": [...]} format
    payload = {
        "instances": test_features.tolist()
    }
    
    print("Sending request with features:")
    print(test_features)
    
    try:
        # Send POST request to TF Serving
        response = requests.post(TF_SERVING_URL, json=payload, timeout=5)
        response.raise_for_status()
        
        # Parse response
        data = response.json()
        predictions = np.array(data["predictions"])
        
        # Display results
        print("\n✓ TF Serving responded successfully!")
        print("\nPredicted music parameters:")
        print("Format: [tempo_bpm, base_frequency, brightness, volume, duration_seconds]")
        for i, pred in enumerate(predictions):
            print(f"Sample {i+1}: {pred}")
        
        # Sanity check ranges
        print("\nSanity checks:")
        print(f"  Tempo range: {predictions[:, 0].min():.1f} - {predictions[:, 0].max():.1f} BPM")
        print(f"  Frequency range: {predictions[:, 1].min():.1f} - {predictions[:, 1].max():.1f} Hz")
        print(f"  Duration range: {predictions[:, 4].min():.1f} - {predictions[:, 4].max():.1f} sec")
        
    except requests.exceptions.ConnectionError:
        print("\n✗ ERROR: Could not connect to TF Serving")
        print("Make sure TF Serving is running: docker compose up tf-serving")
    except requests.exceptions.HTTPError as e:
        print(f"\n✗ ERROR: HTTP {e.response.status_code}")
        print(e.response.text)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")

if __name__ == "__main__":
    main()