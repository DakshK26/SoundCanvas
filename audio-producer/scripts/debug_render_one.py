#!/usr/bin/env python3
"""
Debug script to reproduce zero-length WAV bug (A1.1)

This script tests the audio rendering pipeline in isolation:
1. Load a known-good MIDI file
2. Render using the same path as production
3. Verify output WAV is valid and non-zero

Usage:
    python scripts/debug_render_one.py [midi_file] [output_wav]

Example:
    python scripts/debug_render_one.py tests/fixtures/debug_track.mid debug_out.wav
"""

import sys
import os
import argparse
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from stem_mixer import mix_stems, load_wav, save_wav
from mastering import apply_mastering_chain, apply_simple_limiter
from drum_sampler import DrumSampler
from fx_player import FXPlayer
import subprocess
import numpy as np


def render_midi_to_wav(midi_path: str, output_wav: str, sf2_path: str) -> bool:
    """Render MIDI to WAV using FluidSynth"""
    # Find FluidSynth executable
    fluidsynth_paths = [
        'C:/fluidsynth/bin/fluidsynth.exe',
        '/usr/bin/fluidsynth',
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
            print(f"✗ FluidSynth error: {result.stderr.decode()}")
            return False
        
        return os.path.exists(output_wav) and os.path.getsize(output_wav) > 0
        
    except Exception as e:
        print(f"✗ FluidSynth error: {str(e)}")
        return False


def analyze_wav(wav_path: str) -> dict:
    """
    Analyze WAV file and return detailed statistics
    
    Returns:
        Dict with: sample_count, duration_seconds, peak_amplitude, rms, is_silent
    """
    import wave
    from scipy.io import wavfile
    
    # Get basic info using wave module
    with wave.open(wav_path, 'rb') as wf:
        n_channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        framerate = wf.getframerate()
        n_frames = wf.getnframes()
    
    # Load audio data
    rate, data = wavfile.read(wav_path)
    
    # Convert to float32
    if data.dtype == np.int16:
        data_float = data.astype(np.float32) / 32768.0
    elif data.dtype == np.int32:
        data_float = data.astype(np.float32) / 2147483648.0
    else:
        data_float = data.astype(np.float32)
    
    # Calculate stats
    duration = n_frames / framerate
    peak = np.abs(data_float).max()
    rms = np.sqrt(np.mean(data_float ** 2))
    
    # Check if silent (RMS below -60dB)
    is_silent = rms < 0.001  # -60dB threshold
    
    return {
        'sample_count': n_frames,
        'duration_seconds': duration,
        'peak_amplitude': peak,
        'rms': rms,
        'rms_db': 20 * np.log10(rms) if rms > 0 else -np.inf,
        'is_silent': is_silent,
        'file_size_bytes': os.path.getsize(wav_path),
        'sample_rate': framerate,
        'channels': n_channels
    }


def debug_render_pipeline(midi_path: str, output_path: str, genre: str = 'HOUSE'):
    """
    Run full rendering pipeline with debug output
    
    Steps:
    1. Render MIDI with FluidSynth
    2. Analyze pre-mixing buffer
    3. Apply simple mixing
    4. Analyze post-mixing buffer
    5. Apply mastering
    6. Analyze final output
    """
    print("=" * 60)
    print("DEBUG RENDER PIPELINE")
    print("=" * 60)
    print(f"Input MIDI:  {midi_path}")
    print(f"Output WAV:  {output_path}")
    print(f"Genre:       {genre}")
    print()
    
    # Check inputs
    if not os.path.exists(midi_path):
        print(f"✗ ERROR: MIDI file not found: {midi_path}")
        return False
    
    # Find soundfont
    sf2_paths = [
        'C:/soundfonts/FluidR3_GM.sf2',
        '/sf/FluidR3_GM.sf2',
        '/usr/share/sounds/sf2/FluidR3_GM.sf2'
    ]
    sf2_path = next((p for p in sf2_paths if os.path.exists(p)), None)
    
    if not sf2_path:
        print(f"✗ ERROR: Soundfont not found. Tried: {sf2_paths}")
        return False
    
    print(f"Using soundfont: {sf2_path}")
    print()
    
    # Step 1: Render MIDI to temp WAV
    print("STEP 1: Rendering MIDI with FluidSynth...")
    temp_raw = "/tmp/debug_raw.wav" if os.name != 'nt' else "debug_raw.wav"
    
    if not render_midi_to_wav(midi_path, temp_raw, sf2_path):
        print("✗ FAILED: FluidSynth rendering")
        return False
    
    print("✓ FluidSynth rendering successful")
    
    # Analyze raw output
    try:
        stats = analyze_wav(temp_raw)
        print(f"  Sample count:     {stats['sample_count']:,}")
        print(f"  Duration:         {stats['duration_seconds']:.2f} seconds")
        print(f"  Peak amplitude:   {stats['peak_amplitude']:.4f}")
        print(f"  RMS:              {stats['rms']:.4f} ({stats['rms_db']:.1f} dB)")
        print(f"  File size:        {stats['file_size_bytes']:,} bytes")
        print(f"  Is silent:        {stats['is_silent']}")
        
        if stats['is_silent']:
            print("  ⚠️  WARNING: Output is silent!")
        
        if stats['duration_seconds'] < 1.0:
            print("  ⚠️  WARNING: Duration less than 1 second!")
        
    except Exception as e:
        print(f"  ✗ Analysis failed: {e}")
    
    print()
    
    # Step 2: Apply simple mixing (with normalization)
    print("STEP 2: Applying mixing/normalization...")
    temp_mixed = "/tmp/debug_mixed.wav" if os.name != 'nt' else "debug_mixed.wav"
    
    try:
        # Load and normalize
        rate, data = load_wav(temp_raw)
        
        # Log buffer stats BEFORE any processing
        print(f"  Buffer stats (pre-mix):")
        print(f"    Shape:      {data.shape}")
        print(f"    Min:        {data.min():.4f}")
        print(f"    Max:        {data.max():.4f}")
        print(f"    Mean:       {data.mean():.4f}")
        print(f"    RMS:        {np.sqrt(np.mean(data ** 2)):.4f}")
        
        # Normalize to 0.8 to leave headroom
        peak = np.abs(data).max()
        if peak > 0:
            data = data * (0.8 / peak)
            print(f"  Normalized: peak {peak:.4f} → 0.8")
        else:
            print("  ⚠️  WARNING: Peak is zero, cannot normalize!")
        
        # Log buffer stats AFTER processing
        print(f"  Buffer stats (post-mix):")
        print(f"    Min:        {data.min():.4f}")
        print(f"    Max:        {data.max():.4f}")
        print(f"    RMS:        {np.sqrt(np.mean(data ** 2)):.4f}")
        
        # Save mixed output
        save_wav(temp_mixed, rate, data)
        print("  ✓ Saved mixed WAV")
        
        # Verify file was written
        if not os.path.exists(temp_mixed):
            print("  ✗ ERROR: File not created!")
            return False
        
        file_size = os.path.getsize(temp_mixed)
        print(f"  File size: {file_size:,} bytes")
        
        if file_size == 0:
            print("  ✗ ERROR: File is zero bytes!")
            return False
        
    except Exception as e:
        print(f"  ✗ Mixing failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print()
    
    # Step 3: Apply mastering
    print("STEP 3: Applying mastering chain...")
    
    try:
        # Apply mastering
        success = apply_mastering_chain(temp_mixed, output_path, target_lufs=-14.0)
        
        if not success:
            print("  Mastering failed, applying limiter only...")
            apply_simple_limiter(temp_mixed, output_path)
        else:
            print("  ✓ Mastering chain applied")
        
        # Verify final output
        if not os.path.exists(output_path):
            print("  ✗ ERROR: Final output not created!")
            return False
        
        final_size = os.path.getsize(output_path)
        print(f"  Final file size: {final_size:,} bytes")
        
        if final_size == 0:
            print("  ✗ ERROR: Final file is zero bytes!")
            return False
        
    except Exception as e:
        print(f"  ✗ Mastering failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print()
    
    # Step 4: Analyze final output
    print("STEP 4: Analyzing final output...")
    
    try:
        stats = analyze_wav(output_path)
        print(f"  ✓ Sample count:     {stats['sample_count']:,}")
        print(f"  ✓ Duration:         {stats['duration_seconds']:.2f} seconds")
        print(f"  ✓ Peak amplitude:   {stats['peak_amplitude']:.4f}")
        print(f"  ✓ RMS:              {stats['rms']:.4f} ({stats['rms_db']:.1f} dB)")
        print(f"  ✓ File size:        {stats['file_size_bytes']:,} bytes")
        
        # Check for issues
        issues = []
        if stats['is_silent']:
            issues.append("Output is SILENT")
        if stats['duration_seconds'] < 2.0:
            issues.append(f"Duration too short ({stats['duration_seconds']:.2f}s)")
        if stats['file_size_bytes'] < 1000:
            issues.append(f"File suspiciously small ({stats['file_size_bytes']} bytes)")
        
        if issues:
            print()
            print("  ⚠️  ISSUES DETECTED:")
            for issue in issues:
                print(f"      - {issue}")
            return False
        else:
            print()
            print("  ✅ ALL CHECKS PASSED!")
            return True
        
    except Exception as e:
        print(f"  ✗ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(description='Debug audio rendering pipeline')
    parser.add_argument('midi_file', nargs='?', 
                       help='Input MIDI file (default: tests/fixtures/debug_track.mid)')
    parser.add_argument('output_wav', nargs='?', default='debug_out.wav',
                       help='Output WAV file (default: debug_out.wav)')
    parser.add_argument('--genre', default='HOUSE',
                       choices=['RAP', 'HOUSE', 'RNB', 'EDM_CHILL', 'EDM_DROP'],
                       help='Genre for mixing presets')
    
    args = parser.parse_args()
    
    # Default MIDI file
    midi_file = args.midi_file or 'tests/fixtures/debug_track.mid'
    
    # Check if file exists, try alternative paths
    if not os.path.exists(midi_file):
        # Try cpp-core output directory
        alt_path = '../cpp-core/output/composition.mid'
        if os.path.exists(alt_path):
            print(f"Using alternative MIDI: {alt_path}")
            midi_file = alt_path
        else:
            print(f"ERROR: MIDI file not found: {midi_file}")
            print(f"Tried: {midi_file}, {alt_path}")
            return 1
    
    # Run debug pipeline
    success = debug_render_pipeline(midi_file, args.output_wav, args.genre)
    
    if success:
        print()
        print("=" * 60)
        print("✅ DEBUG SUCCESSFUL - No zero-length WAV bug detected")
        print(f"Output: {args.output_wav}")
        print("=" * 60)
        return 0
    else:
        print()
        print("=" * 60)
        print("✗ DEBUG FAILED - Zero-length WAV bug reproduced")
        print("=" * 60)
        return 1


if __name__ == '__main__':
    sys.exit(main())
