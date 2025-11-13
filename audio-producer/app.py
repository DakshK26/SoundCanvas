"""
Audio Producer Service - Multi-stem mixing and mastering
Flask app that takes MIDI + genre template and produces mixed/mastered WAV

Phase 9: Enhanced with sample-based drums, genre-aware mixing, sidechain, FX
"""
from flask import Flask, request, jsonify
import os
import subprocess
import tempfile
from typing import Dict, List, Optional
import json

from mastering import apply_mastering_chain, apply_simple_limiter, measure_lufs
from stem_mixer import mix_stems, mix_stems_simple
from drum_sampler import DrumSampler  # Phase 9
from fx_player import FXPlayer  # Phase 9
from mix.schema import get_preset_for_genre  # Phase 9

app = Flask(__name__)

# Configuration
# Try Windows path first, then Docker path
if os.path.exists('C:/soundfonts/FluidR3_GM.sf2'):
    SF2_PATH = os.getenv('SF2_PATH', 'C:/soundfonts/FluidR3_GM.sf2')
else:
    SF2_PATH = os.getenv('SF2_PATH', '/sf/FluidR3_GM.sf2')
DATA_DIR = '/data'
STEMS_DIR = os.path.join(DATA_DIR, 'stems')
PATTERNS_DIR = os.path.join(DATA_DIR, 'patterns')

# Phase 9: Asset paths
ASSETS_DIR = os.path.join(os.path.dirname(__file__), 'assets')
MIX_PRESETS_DIR = os.path.join(os.path.dirname(__file__), 'mix', 'presets')
FX_CONFIG_PATH = os.path.join(ASSETS_DIR, 'fx', 'fx_config.yaml')

# Ensure directories exist
os.makedirs(STEMS_DIR, exist_ok=True)

# Phase 9: Initialize drum sampler and FX player
drum_sampler = None
fx_player = None

try:
    drum_sampler = DrumSampler(
        kits_dir=os.path.join(ASSETS_DIR, 'kits'),
        samples_dir=os.path.join(ASSETS_DIR, 'samples')
    )
    print("✓ Drum sampler initialized")
except Exception as e:
    print(f"Warning: Drum sampler failed to initialize: {e}")

try:
    fx_player = FXPlayer(
        fx_config_path=FX_CONFIG_PATH,
        assets_dir=ASSETS_DIR
    )
    print("✓ FX player initialized")
except Exception as e:
    print(f"Warning: FX player failed to initialize: {e}")


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
    # Find FluidSynth executable
    fluidsynth_paths = [
        'C:/fluidsynth/bin/fluidsynth.exe',
        'fluidsynth'  # Try PATH
    ]
    fluidsynth_exe = next((p for p in fluidsynth_paths if os.path.exists(p) or p == 'fluidsynth'), 'fluidsynth')
    
    try:
        cmd = [
            fluidsynth_exe,
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
    
    Phase 9: Enhanced with sample-based drums, genre-aware mixing, FX
    
    Request JSON:
    {
        "midi_path": "/data/composition.mid",  # Main MIDI file
        "stems": {  # Optional: individual MIDI stems (if not using main MIDI)
            "kick": "/data/midi/kick.mid",
            "bass": "/data/midi/bass.mid",
            "lead": "/data/midi/lead.mid"
        },
        "output_path": "/data/audio/final.wav",
        "genre": "HOUSE",  # EDM_CHILL, EDM_DROP, HOUSE, RAP, RNB
        "apply_mastering": true,
        "use_sample_drums": true,  # Phase 9: Use sample-based drums
        "render_fx": true  # Phase 9: Render FX stem
    }
    
    Response:
    {
        "status": "success",
        "output_path": "/data/audio/final.wav",
        "lufs": -14.2,
        "duration_sec": 67.5,
        "genre": "HOUSE"
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'status': 'error', 'message': 'No JSON data'}), 400
        
        # Parse request
        midi_path = data.get('midi_path')  # Phase 9: Main MIDI file
        stems_midi = data.get('stems', {})
        output_path = data.get('output_path')
        genre = data.get('genre', 'EDM_DROP')
        apply_mastering = data.get('apply_mastering', True)
        use_sample_drums = data.get('use_sample_drums', True)  # Phase 9
        render_fx = data.get('render_fx', True)  # Phase 9
        
        if not output_path:
            return jsonify({'status': 'error', 'message': 'Missing output_path'}), 400
        
        if not midi_path and not stems_midi:
            return jsonify({'status': 'error', 'message': 'Need midi_path or stems'}), 400
        
        print(f"Producing track: genre={genre}, output={output_path}")
        
        # Phase 9: Load genre-specific mix preset
        mix_preset = None
        try:
            mix_preset = get_preset_for_genre(genre, MIX_PRESETS_DIR)
            print(f"  Loaded mix preset: {genre}")
        except Exception as e:
            print(f"  Warning: Failed to load mix preset: {e}")
        
        # Step 1: Render MIDI stems to WAV
        stem_wavs = {}
        temp_stems = []
        
        # Phase 9: Use sample-based drums if enabled
        if use_sample_drums and drum_sampler and midi_path:
            print("  Rendering drums with samples...")
            
            drums_wav = os.path.join(STEMS_DIR, f"drums_{os.getpid()}.wav")
            temp_stems.append(drums_wav)
            
            # Get genre-specific drum kit
            kit_name = {
                'RAP': 'trap_808',
                'HOUSE': 'house',
                'RNB': 'rnb_soft',
                'EDM_DROP': 'house',  # Use house kit for EDM
                'EDM_CHILL': 'rnb_soft'  # Softer drums for chill
            }.get(genre, 'house')
            
            try:
                drum_sampler.render_midi(midi_path, drums_wav, kit_name=kit_name)
                stem_wavs['drums'] = drums_wav
                print(f"    ✓ Drums rendered with {kit_name} kit")
            except Exception as e:
                print(f"    Warning: Sample drum rendering failed: {e}")
                # Fallback to FluidSynth
                if render_midi_to_wav(midi_path, drums_wav):
                    stem_wavs['drums'] = drums_wav
                    print("    ✓ Drums rendered with FluidSynth (fallback)")
        
        # Render other stems (bass, lead, pad, etc.)
        if stems_midi:
            for stem_name, stem_midi in stems_midi.items():
                if not os.path.exists(stem_midi):
                    print(f"  Warning: MIDI not found: {stem_midi}")
                    continue
                
                temp_wav = os.path.join(STEMS_DIR, f"{stem_name}_{os.getpid()}.wav")
                temp_stems.append(temp_wav)
                
                if render_midi_to_wav(stem_midi, temp_wav):
                    stem_wavs[stem_name] = temp_wav
                    print(f"  ✓ Rendered {stem_name}")
                else:
                    print(f"  ✗ Failed to render {stem_name}")
        
        elif midi_path and not use_sample_drums:
            # Render full MIDI with FluidSynth (old path)
            full_wav = os.path.join(STEMS_DIR, f"full_{os.getpid()}.wav")
            temp_stems.append(full_wav)
            
            if render_midi_to_wav(midi_path, full_wav):
                stem_wavs['full'] = full_wav
                print(f"  ✓ Rendered full MIDI")
        
        if not stem_wavs:
            return jsonify({'status': 'error', 'message': 'No stems rendered'}), 500
        
        # Phase 9: Render FX stem
        if render_fx and fx_player and midi_path:
            print("  Rendering FX stem...")
            fx_wav = os.path.join(STEMS_DIR, f"fx_{os.getpid()}.wav")
            temp_stems.append(fx_wav)
            
            try:
                # Estimate duration (rough)
                import mido
                midi_file = mido.MidiFile(midi_path)
                duration = midi_file.length if hasattr(midi_file, 'length') else 120.0
                
                fx_player.render_fx_stem(midi_path, fx_wav, duration)
                stem_wavs['fx'] = fx_wav
                print(f"    ✓ FX stem rendered")
            except Exception as e:
                print(f"    Warning: FX rendering failed: {e}")
        
        # Step 2: Mix stems with genre-aware settings
        temp_mixed = tempfile.NamedTemporaryFile(suffix='.wav', delete=False).name
        
        # Apply stem gains from mix preset
        stem_gains = {}
        if mix_preset:
            for bus_name, bus_preset in mix_preset.buses.items():
                stem_gains[bus_name] = bus_preset.gain
        
        # Apply sidechain with MIDI-based timing
        sidechain_amount = 0.5
        sidechain_targets = ['bass', 'lead', 'pad', 'arp']
        
        if mix_preset and mix_preset.bus.sidechain_amount > 0:
            sidechain_amount = mix_preset.bus.sidechain_amount
            print(f"  Sidechain amount: {sidechain_amount}")
        
        print(f"  Mixing stems with sidechain...")
        mix_success = mix_stems(
            stem_wavs, 
            temp_mixed,
            apply_sidechain_to=sidechain_targets,
            stem_gains=stem_gains,
            midi_path=midi_path,  # Phase 9: MIDI-based sidechain
            sidechain_amount=sidechain_amount
        )
        
        if not mix_success:
            return jsonify({'status': 'error', 'message': 'Mixing failed'}), 500
        
        # Step 3: Apply mastering chain
        if apply_mastering:
            print("  Applying mastering...")
            master_success = apply_mastering_chain(temp_mixed, output_path, target_lufs=-14.0)
            
            if not master_success:
                print("  Mastering failed, applying limiter")
                apply_simple_limiter(temp_mixed, output_path)
        else:
            print("  Applying limiter only...")
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
        
        # Estimate duration
        duration_sec = (file_size - 44) / (44100 * 2 * 2)
        
        return jsonify({
            'status': 'success',
            'output_path': output_path,
            'file_size': file_size,
            'lufs': round(lufs, 2),
            'duration_sec': round(duration_sec, 2),
            'stems_count': len(stem_wavs),
            'genre': genre,
            'sample_drums': use_sample_drums and 'drums' in stem_wavs,
            'fx_rendered': 'fx' in stem_wavs,
            'mastering_applied': apply_mastering
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
