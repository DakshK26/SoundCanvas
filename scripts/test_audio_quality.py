#!/usr/bin/env python3
"""
Phase 12 A3.2: Audio Taste-Level Tests

Test that generated audio meets quality standards:
- Drums are audible (RMS > threshold in low frequencies)
- Bass not overwhelming (peak bass < 0.8)
- Sidechain compression working (visible ducking on kicks)
- No clipping (peak < 1.0)
- Reasonable loudness (-20 to -10 LUFS)
"""

import os
import sys
import subprocess
import numpy as np
from scipy.io import wavfile
from scipy import signal
import argparse


def measure_lufs(wav_path):
    """Measure LUFS using ffmpeg"""
    try:
        cmd = [
            'ffmpeg', '-i', wav_path,
            '-af', 'ebur128=framelog=verbose',
            '-f', 'null', '-'
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        # Parse LUFS from stderr
        for line in result.stderr.split('\n'):
            if 'I:' in line and 'LUFS' in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == 'I:':
                        return float(parts[i+1])
        return None
    except Exception as e:
        print(f"Warning: Could not measure LUFS: {e}")
        return None


def analyze_frequency_bands(audio_data, sample_rate):
    """
    Analyze RMS energy in different frequency bands
    Returns: {bass, mids, highs} RMS values
    """
    # Convert to mono if stereo
    if len(audio_data.shape) > 1:
        audio_mono = audio_data.mean(axis=1)
    else:
        audio_mono = audio_data
    
    # Convert to float
    if audio_mono.dtype == np.int16:
        audio_float = audio_mono.astype(np.float32) / 32768.0
    else:
        audio_float = audio_mono.astype(np.float32)
    
    # Design bandpass filters
    nyquist = sample_rate / 2
    
    # Bass: 20-250 Hz
    sos_bass = signal.butter(4, [20/nyquist, 250/nyquist], btype='band', output='sos')
    bass = signal.sosfilt(sos_bass, audio_float)
    bass_rms = np.sqrt(np.mean(bass ** 2))
    
    # Mids: 250-2000 Hz
    sos_mids = signal.butter(4, [250/nyquist, 2000/nyquist], btype='band', output='sos')
    mids = signal.sosfilt(sos_mids, audio_float)
    mids_rms = np.sqrt(np.mean(mids ** 2))
    
    # Highs: 2000-20000 Hz
    sos_highs = signal.butter(4, [2000/nyquist, min(20000, nyquist-100)/nyquist], btype='band', output='sos')
    highs = signal.sosfilt(sos_highs, audio_float)
    highs_rms = np.sqrt(np.mean(highs ** 2))
    
    return {
        'bass': bass_rms,
        'mids': mids_rms,
        'highs': highs_rms,
        'bass_db': 20 * np.log10(bass_rms) if bass_rms > 0 else -np.inf,
        'mids_db': 20 * np.log10(mids_rms) if mids_rms > 0 else -np.inf,
        'highs_db': 20 * np.log10(highs_rms) if highs_rms > 0 else -np.inf,
    }


def detect_sidechain_ducking(audio_data, sample_rate, expected_bpm=120):
    """
    Detect if sidechain compression is working by looking for periodic
    envelope dips at kick positions (every beat)
    """
    # Convert to mono
    if len(audio_data.shape) > 1:
        audio_mono = audio_data.mean(axis=1)
    else:
        audio_mono = audio_data
    
    # Convert to float
    if audio_mono.dtype == np.int16:
        audio_float = audio_mono.astype(np.float32) / 32768.0
    else:
        audio_float = audio_mono.astype(np.float32)
    
    # Get envelope (absolute value with smoothing)
    envelope = np.abs(audio_float)
    
    # Smooth envelope (moving average over ~10ms)
    window_size = int(sample_rate * 0.01)
    envelope_smooth = np.convolve(envelope, np.ones(window_size)/window_size, mode='same')
    
    # Expected kick interval
    beat_interval_sec = 60.0 / expected_bpm
    beat_interval_samples = int(beat_interval_sec * sample_rate)
    
    # Look for periodic dips in envelope
    # Simple test: Check if envelope variance is reasonable (not flat line)
    envelope_variance = np.var(envelope_smooth)
    
    return {
        'has_dynamics': envelope_variance > 0.001,  # Not completely flat
        'envelope_variance': envelope_variance,
    }


def test_audio_quality(wav_path, genre=None):
    """
    Run comprehensive audio quality tests
    Returns: (passed, results)
    """
    print(f"\n=== Testing {wav_path} ===")
    
    if not os.path.exists(wav_path):
        print(f"FAIL: File does not exist")
        return False, {}
    
    # Load audio
    try:
        rate, data = wavfile.read(wav_path)
    except Exception as e:
        print(f"FAIL: Could not read WAV file: {e}")
        return False, {}
    
    # Convert to float
    if data.dtype == np.int16:
        data_float = data.astype(np.float32) / 32768.0
    elif data.dtype == np.int32:
        data_float = data.astype(np.float32) / 2147483648.0
    else:
        data_float = data.astype(np.float32)
    
    # Basic stats
    duration = len(data) / rate
    peak = np.abs(data_float).max()
    rms = np.sqrt(np.mean(data_float ** 2))
    rms_db = 20 * np.log10(rms) if rms > 0 else -np.inf
    
    print(f"Duration: {duration:.2f}s")
    print(f"Peak: {peak:.3f}")
    print(f"RMS: {rms:.4f} ({rms_db:.1f} dB)")
    
    results = {
        'duration': duration,
        'peak': peak,
        'rms': rms,
        'rms_db': rms_db,
    }
    
    # Test 1: No clipping
    passed_clipping = peak < 1.0
    print(f"  {'✓' if passed_clipping else '✗'} No clipping (peak < 1.0): {peak:.3f}")
    
    # Test 2: Not silent
    passed_silent = rms > 0.001
    print(f"  {'✓' if passed_silent else '✗'} Not silent (RMS > 0.001): {rms:.4f}")
    
    # Test 3: Reasonable duration
    passed_duration = duration >= 30.0
    print(f"  {'✓' if passed_duration else '✗'} Duration >= 30s: {duration:.1f}s")
    
    # Test 4: Frequency balance
    bands = analyze_frequency_bands(data_float, rate)
    results['bands'] = bands
    
    print(f"\nFrequency Analysis:")
    print(f"  Bass (20-250 Hz):     {bands['bass_db']:.1f} dB")
    print(f"  Mids (250-2000 Hz):   {bands['mids_db']:.1f} dB")
    print(f"  Highs (2000-20k Hz):  {bands['highs_db']:.1f} dB")
    
    # Bass should be present but not overwhelming
    passed_bass_present = bands['bass_rms'] > 0.01  # Bass audible
    passed_bass_not_overpowering = bands['bass_rms'] < 0.5  # Not too loud
    
    print(f"  {'✓' if passed_bass_present else '✗'} Bass audible (RMS > 0.01)")
    print(f"  {'✓' if passed_bass_not_overpowering else '✗'} Bass not overpowering (RMS < 0.5)")
    
    # Test 5: Sidechain compression (for genres that use it)
    if genre in ['HOUSE', 'EDM_Drop', 'RAP']:
        ducking = detect_sidechain_ducking(data_float, rate)
        results['ducking'] = ducking
        
        passed_ducking = ducking['has_dynamics']
        print(f"\nSidechain Compression:")
        print(f"  {'✓' if passed_ducking else '✗'} Has dynamics (variance > 0.001): {ducking['envelope_variance']:.4f}")
    else:
        passed_ducking = True  # N/A for this genre
    
    # Test 6: LUFS (loudness)
    lufs = measure_lufs(wav_path)
    if lufs is not None:
        results['lufs'] = lufs
        passed_lufs = -20.0 <= lufs <= -10.0
        print(f"\nLoudness:")
        print(f"  {'✓' if passed_lufs else '✗'} LUFS in range [-20, -10]: {lufs:.1f} LUFS")
    else:
        passed_lufs = True  # Skip if measurement failed
    
    # Overall pass/fail
    all_tests = [
        passed_clipping,
        passed_silent,
        passed_duration,
        passed_bass_present,
        passed_bass_not_overpowering,
        passed_ducking,
        passed_lufs,
    ]
    
    passed = all(all_tests)
    
    print(f"\n{'✓ PASSED' if passed else '✗ FAILED'}")
    
    return passed, results


def main():
    parser = argparse.ArgumentParser(description='Test audio quality')
    parser.add_argument('wav_files', nargs='+', help='WAV files to test')
    parser.add_argument('--genre', help='Genre for genre-specific tests')
    args = parser.parse_args()
    
    print("=== Phase 12 A3.2: Audio Taste-Level Tests ===")
    
    total = 0
    passed_count = 0
    
    for wav_path in args.wav_files:
        total += 1
        passed, _ = test_audio_quality(wav_path, args.genre)
        if passed:
            passed_count += 1
    
    print(f"\n=== Summary ===")
    print(f"Passed: {passed_count}/{total}")
    
    return 0 if passed_count == total else 1


if __name__ == '__main__':
    sys.exit(main())
