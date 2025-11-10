#!/usr/bin/env python3
"""
Test script for SoundCanvas HTTP /generate endpoint.
Usage: python3 scripts/test_http_generate.py <image_path>
"""

import os
import sys
import requests

# Default to localhost, can override with SC_HTTP_URL env var
DEFAULT_URL = "http://localhost:8080/generate"

def main():
    if len(sys.argv) != 2:
        print("Usage: test_http_generate.py <image_path>")
        print("Example: python3 scripts/test_http_generate.py cpp-core/examples/test_image.png")
        sys.exit(1)

    image_path = sys.argv[1]
    url = os.environ.get("SC_HTTP_URL", DEFAULT_URL)

    # Build request payload
    payload = {
        "image_path": image_path,
        "mode": "model"
    }

    print(f"Testing HTTP endpoint: {url}")
    print(f"Image path: {image_path}")
    print(f"Mode: model")
    print("-" * 50)

    try:
        response = requests.post(url, json=payload, timeout=30)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Body:")
        print(response.text)
        
        if response.status_code == 200:
            data = response.json()
            print("\n✓ Success!")
            print(f"  Audio file: {data.get('audio_path')}")
            print(f"  Music parameters:")
            params = data.get('params', {})
            for key, value in params.items():
                print(f"    {key}: {value}")
        else:
            print("\n✗ Request failed")
            
        return 0 if response.status_code == 200 else 1
        
    except requests.exceptions.ConnectionError:
        print("\n✗ ERROR: Could not connect to server")
        print("Make sure the server is running: make run-local")
        return 1
    except requests.exceptions.Timeout:
        print("\n✗ ERROR: Request timed out")
        return 1
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())