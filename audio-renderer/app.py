#!/usr/bin/env python3
"""
Audio Renderer Service
Converts MIDI files to WAV using FluidSynth with optional ambience mixing
"""

import os
import subprocess
import json
from pathlib import Path
from flask import Flask, request, jsonify
import numpy as np
from scipy.io import wavfile

app = Flask(__name__)

# Configuration
SF2_PATH = os.getenv('SF2_PATH', '/sf/FluidR3_GM.sf2')
SAMPLE_RATE = 44100

# Ambience file mapping
AMBIENCE_FILES = {
    'none': None,
    'ocean': '/data/ambience/ocean.wav',
    'rain': '/data/ambience/rain.wav',
    'forest': '/data/ambience/forest.wav',
    'city': '/data/ambience/city.wav',
}


def load_wav(path):
    """Load a WAV file and return sample rate and normalized float data"""
    try:
        rate, data = wavfile.read(path)
        
        # Convert to float32 normalized to [-1, 1]
        if data.dtype == np.int16:
            data = data.astype(np.float32) / 32768.0
        elif data.dtype == np.int32:
            data = data.astype(np.float32) / 2147483648.0
        elif data.dtype == np.uint8:
            data = (data.astype(np.float32) - 128.0) / 128.0
        
        # Convert stereo to mono if needed
        if len(data.shape) > 1:
            data = data.mean(axis=1)
        
        return rate, data
    except Exception as e:
        print(f"[WARN] Failed to load WAV {path}: {e}")
        return None, None


def save_wav(path, rate, data):
    """Save normalized float data as 16-bit WAV"""
    # Clip and convert to int16
    data_clipped = np.clip(data, -1.0, 1.0)
    data_int16 = (data_clipped * 32767.0).astype(np.int16)
    wavfile.write(path, rate, data_int16)


def mix_ambience(main_path, ambience_type, mood_score, output_path):
    """
    Mix ambience layer into the main audio
    
    Args:
        main_path: Path to main rendered audio
        ambience_type: Type of ambience (ocean, rain, forest, city, none)
        mood_score: 0.0-1.0, affects ambience volume
        output_path: Where to save the final mixed audio
    """
    # Load main audio
    main_rate, main_data = load_wav(main_path)
    if main_data is None:
        print(f"[ERROR] Could not load main audio: {main_path}")
        return False
    
    # If no ambience, just copy main to output
    if ambience_type == 'none' or ambience_type not in AMBIENCE_FILES:
        save_wav(output_path, main_rate, main_data)
        return True
    
    # Load ambience
    ambience_path = AMBIENCE_FILES[ambience_type]
    if not os.path.exists(ambience_path):
        print(f"[WARN] Ambience file not found: {ambience_path}, skipping ambience layer")
        save_wav(output_path, main_rate, main_data)
        return True
    
    amb_rate, amb_data = load_wav(ambience_path)
    if amb_data is None:
        print(f"[WARN] Could not load ambience, using main audio only")
        save_wav(output_path, main_rate, main_data)
        return True
    
    # Resample ambience if needed (simple repeat/truncate, not ideal but works)
    if amb_rate != main_rate:
        print(f"[WARN] Ambience sample rate {amb_rate} != {main_rate}, using as-is")
    
    # Loop ambience to match main audio length
    main_len = len(main_data)
    if len(amb_data) < main_len:
        # Loop ambience
        repeats = (main_len // len(amb_data)) + 1
        amb_data = np.tile(amb_data, repeats)[:main_len]
    else:
        # Truncate
        amb_data = amb_data[:main_len]
    
    # Calculate ambience gain based on mood score
    # Lower mood = quieter ambience, higher mood = louder ambience
    base_gain = 0.1  # -20 dB base
    mood_gain = 0.3  # Up to +0.3 for high mood
    ambience_gain = base_gain + (mood_score * mood_gain)
    
    print(f"[INFO] Mixing {ambience_type} ambience at gain {ambience_gain:.3f} (mood: {mood_score:.2f})")
    
    # Mix
    mixed = main_data + (amb_data * ambience_gain)
    
    # Simple limiter to prevent clipping
    max_val = np.abs(mixed).max()
    if max_val > 0.95:
        mixed = mixed * (0.95 / max_val)
        print(f"[INFO] Applied limiting, reduced by {max_val/0.95:.2f}x")
    
    # Save
    save_wav(output_path, main_rate, mixed)
    return True


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'audio-renderer'}), 200


@app.route('/render', methods=['POST'])
def render():
    """
    Render MIDI to WAV using FluidSynth with optional ambience
    
    Request JSON:
    {
        "midi_path": "/data/midi/ocean.mid",
        "output_path": "/data/audio/ocean.wav",
        "ambience_type": "ocean",  # optional: ocean, rain, forest, city, none
        "mood_score": 0.8          # optional: 0.0-1.0
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        midi_path = data.get('midi_path')
        output_path = data.get('output_path')
        ambience_type = data.get('ambience_type', 'none').lower()
        mood_score = float(data.get('mood_score', 0.5))
        
        if not midi_path or not output_path:
            return jsonify({'error': 'midi_path and output_path required'}), 400
        
        # Validate paths
        if not os.path.exists(midi_path):
            return jsonify({'error': f'MIDI file not found: {midi_path}'}), 404
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        print(f"[INFO] Rendering MIDI: {midi_path}")
        print(f"[INFO]   Output: {output_path}")
        print(f"[INFO]   Ambience: {ambience_type}, Mood: {mood_score:.2f}")
        
        # Create temporary file for FluidSynth output
        temp_output = output_path.replace('.wav', '_temp.wav')
        
        # Run FluidSynth
        cmd = [
            'fluidsynth',
            '-ni',              # No interactive shell
            SF2_PATH,           # Soundfont
            midi_path,          # Input MIDI
            '-F', temp_output,  # Output file
            '-r', str(SAMPLE_RATE),  # Sample rate
            '-g', '0.5',        # Gain (0.5 to prevent clipping)
        ]
        
        print(f"[INFO] Running: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30  # 30 second timeout
        )
        
        if result.returncode != 0:
            print(f"[ERROR] FluidSynth failed:")
            print(f"  stdout: {result.stdout}")
            print(f"  stderr: {result.stderr}")
            return jsonify({
                'error': 'FluidSynth rendering failed',
                'details': result.stderr
            }), 500
        
        if not os.path.exists(temp_output):
            return jsonify({'error': 'FluidSynth did not create output file'}), 500
        
        # Mix ambience if requested
        success = mix_ambience(temp_output, ambience_type, mood_score, output_path)
        
        # Clean up temp file
        if os.path.exists(temp_output):
            os.remove(temp_output)
        
        if not success:
            return jsonify({'error': 'Ambience mixing failed'}), 500
        
        # Get output file size
        file_size = os.path.getsize(output_path)
        
        print(f"[INFO] Rendering complete: {output_path} ({file_size} bytes)")
        
        return jsonify({
            'status': 'success',
            'output_path': output_path,
            'file_size': file_size,
            'ambience_applied': ambience_type != 'none'
        }), 200
        
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Rendering timeout (>30s)'}), 500
    except Exception as e:
        print(f"[ERROR] Rendering failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print(f"[INFO] Audio Renderer Service starting...")
    print(f"[INFO] Soundfont: {SF2_PATH}")
    print(f"[INFO] Sample rate: {SAMPLE_RATE} Hz")
    
    # Check soundfont exists
    if not os.path.exists(SF2_PATH):
        print(f"[WARN] Soundfont not found: {SF2_PATH}")
    
    app.run(host='0.0.0.0', port=9000, debug=False)
