"""
Audio Producer Service - Multi-stem mixing and mastering
Flask app that takes MIDI + genre template and produces mixed/mastered WAV
"""
from flask import Flask, request, jsonify
import os
import subprocess
import tempfile
from typing import Dict, List, Optional
import json

from mastering import apply_mastering_chain, apply_simple_limiter, measure_lufs
from stem_mixer import mix_stems, mix_stems_simple

app = Flask(__name__)

# Configuration
SF2_PATH = os.getenv('SF2_PATH', '/sf/FluidR3_GM.sf2')
DATA_DIR = '/data'
STEMS_DIR = os.path.join(DATA_DIR, 'stems')
PATTERNS_DIR = os.path.join(DATA_DIR, 'patterns')

# Ensure directories exist
os.makedirs(STEMS_DIR, exist_ok=True)


def render_midi_to_wav(midi_path: str, output_wav: str, sf2_path: str = SF2_PATH) -> bool:
    """
    Render MIDI to WAV using FluidSynth
    
    Args:
        midi_path: Path to MIDI file
        output_wav: Output WAV path
        sf2_path: Path to soundfont
    
    Returns:
        True if successful
    """
    try:
        cmd = [
            'fluidsynth',
            '-ni',              # Non-interactive
            '-g', '1.0',        # Gain
            '-r', '44100',      # Sample rate
            sf2_path,
            midi_path,
            '-F', output_wav,   # Output to file
            '-O', 's16'         # 16-bit samples
        ]
        
        result = subprocess.run(cmd, capture_output=True, timeout=60)
        
        if result.returncode != 0:
            print(f"FluidSynth error: {result.stderr.decode()}")
            return False
        
        return os.path.exists(output_wav) and os.path.getsize(output_wav) > 0
        
    except subprocess.TimeoutExpired:
        print("FluidSynth timeout")
        return False
    except Exception as e:
        print(f"FluidSynth error: {str(e)}")
        return False


def extract_midi_track(midi_path: str, track_num: int, output_path: str) -> bool:
    """
    Extract single track from MIDI file (for multi-track MIDI)
    Uses Python's mido library if available, otherwise renders full MIDI
    
    Args:
        midi_path: Input MIDI path
        track_num: Track number to extract
        output_path: Output MIDI path
    
    Returns:
        True if successful
    """
    try:
        # For now, just copy the MIDI (Person A will provide per-instrument MIDIs)
        import shutil
        shutil.copy(midi_path, output_path)
        return True
    except Exception as e:
        print(f"MIDI track extraction error: {str(e)}")
        return False


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'audio-producer'}), 200


@app.route('/produce', methods=['POST'])
def produce():
    """
    Produce final track from MIDI stems + genre template
    
    Request JSON:
    {
        "stems": {
            "kick": "/data/midi/kick.mid",
            "bass": "/data/midi/bass.mid",
            "lead": "/data/midi/lead.mid"
        },
        "output_path": "/data/audio/final.wav",
        "genre": "EDM_Drop",
        "apply_mastering": true,
        "apply_sidechain": true,
        "sidechain_targets": ["bass", "lead", "pad"]
    }
    
    Response:
    {
        "status": "success",
        "output_path": "/data/audio/final.wav",
        "lufs": -14.2,
        "duration_sec": 67.5
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'status': 'error', 'message': 'No JSON data'}), 400
        
        stems_midi = data.get('stems', {})
        output_path = data.get('output_path')
        genre = data.get('genre', 'EDM_Drop')
        apply_mastering = data.get('apply_mastering', True)
        apply_sidechain_fx = data.get('apply_sidechain', True)
        sidechain_targets = data.get('sidechain_targets', ['bass', 'lead', 'pad'])
        
        if not output_path:
            return jsonify({'status': 'error', 'message': 'Missing output_path'}), 400
        
        if not stems_midi:
            return jsonify({'status': 'error', 'message': 'No stems provided'}), 400
        
        print(f"Producing track: {len(stems_midi)} stems -> {output_path}")
        
        # Step 1: Render each MIDI stem to WAV
        stem_wavs = {}
        temp_stems = []
        
        for stem_name, midi_path in stems_midi.items():
            if not os.path.exists(midi_path):
                print(f"Warning: MIDI not found: {midi_path}")
                continue
            
            # Render to temp WAV
            temp_wav = os.path.join(STEMS_DIR, f"{stem_name}_{os.getpid()}.wav")
            temp_stems.append(temp_wav)
            
            if render_midi_to_wav(midi_path, temp_wav):
                stem_wavs[stem_name] = temp_wav
                print(f"  Rendered {stem_name}: {temp_wav}")
            else:
                print(f"  Failed to render {stem_name}")
        
        if not stem_wavs:
            return jsonify({'status': 'error', 'message': 'No stems rendered successfully'}), 500
        
        # Step 2: Mix stems with optional sidechain
        temp_mixed = tempfile.NamedTemporaryFile(suffix='.wav', delete=False).name
        
        if apply_sidechain_fx and 'kick' in stem_wavs:
            print(f"  Mixing with sidechain on: {sidechain_targets}")
            mix_success = mix_stems(stem_wavs, temp_mixed, 
                                   apply_sidechain_to=sidechain_targets)
        else:
            print("  Mixing without sidechain")
            mix_success = mix_stems(stem_wavs, temp_mixed, 
                                   apply_sidechain_to=[])
        
        if not mix_success:
            return jsonify({'status': 'error', 'message': 'Mixing failed'}), 500
        
        # Step 3: Apply mastering chain
        if apply_mastering:
            print("  Applying mastering chain...")
            master_success = apply_mastering_chain(temp_mixed, output_path, target_lufs=-14.0)
            
            if not master_success:
                print("  Mastering failed, applying simple limiter")
                apply_simple_limiter(temp_mixed, output_path)
        else:
            print("  Skipping mastering, applying limiter only")
            apply_simple_limiter(temp_mixed, output_path)
        
        # Cleanup temp files
        for temp_file in temp_stems:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        
        if os.path.exists(temp_mixed):
            os.remove(temp_mixed)
        
        # Measure final output
        file_size = os.path.getsize(output_path)
        lufs = measure_lufs(output_path)
        
        # Estimate duration (rough calculation)
        # WAV: bytes = sample_rate * channels * bytes_per_sample * duration
        # 44100 * 2 * 2 * duration = file_size - 44 (header)
        duration_sec = (file_size - 44) / (44100 * 2 * 2)
        
        return jsonify({
            'status': 'success',
            'output_path': output_path,
            'file_size': file_size,
            'lufs': round(lufs, 2),
            'duration_sec': round(duration_sec, 2),
            'stems_count': len(stem_wavs),
            'mastering_applied': apply_mastering,
            'sidechain_applied': apply_sidechain_fx
        }), 200
        
    except Exception as e:
        print(f"Production error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/render-stem', methods=['POST'])
def render_stem():
    """
    Simple endpoint to render single MIDI to WAV (no mixing/mastering)
    
    Request:
    {
        "midi_path": "/data/midi/kick.mid",
        "output_path": "/data/stems/kick.wav"
    }
    """
    try:
        data = request.get_json()
        midi_path = data.get('midi_path')
        output_path = data.get('output_path')
        
        if not midi_path or not output_path:
            return jsonify({'status': 'error', 'message': 'Missing paths'}), 400
        
        if not os.path.exists(midi_path):
            return jsonify({'status': 'error', 'message': 'MIDI file not found'}), 404
        
        success = render_midi_to_wav(midi_path, output_path)
        
        if success:
            return jsonify({
                'status': 'success',
                'output_path': output_path,
                'file_size': os.path.getsize(output_path)
            }), 200
        else:
            return jsonify({'status': 'error', 'message': 'Rendering failed'}), 500
            
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


if __name__ == '__main__':
    print(f"Audio Producer Service starting...")
    print(f"  Soundfont: {SF2_PATH}")
    print(f"  Data dir: {DATA_DIR}")
    print(f"  Stems dir: {STEMS_DIR}")
    
    if not os.path.exists(SF2_PATH):
        print(f"WARNING: Soundfont not found: {SF2_PATH}")
    
    app.run(host='0.0.0.0', port=9001, debug=False)
