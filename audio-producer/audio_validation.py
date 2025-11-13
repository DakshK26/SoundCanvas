"""
Audio Validation - Safety net for zero-length/silent tracks (A1.4)

This module provides validation functions to ensure generated audio meets
minimum quality standards before marking a job as COMPLETE.
"""
import wave
import numpy as np
from scipy.io import wavfile
from typing import Tuple, Optional


class AudioValidationError(Exception):
    """Raised when audio fails validation"""
    pass


def validate_audio_file(wav_path: str, 
                       min_duration_sec: float = 2.0,
                       min_rms_db: float = -60.0) -> Tuple[bool, Optional[str]]:
    """
    Validate that a WAV file meets minimum quality standards
    
    Args:
        wav_path: Path to WAV file
        min_duration_sec: Minimum duration in seconds (default: 2.0)
        min_rms_db: Minimum RMS level in dB (default: -60.0 = very quiet threshold)
    
    Returns:
        Tuple of (is_valid, error_message)
        - (True, None) if valid
        - (False, "reason") if invalid
    """
    try:
        # Check 1: File exists and has non-zero size
        import os
        if not os.path.exists(wav_path):
            return False, f"File does not exist: {wav_path}"
        
        file_size = os.path.getsize(wav_path)
        if file_size == 0:
            return False, "File is zero bytes"
        
        if file_size < 1000:  # WAV header alone is 44 bytes
            return False, f"File suspiciously small ({file_size} bytes)"
        
        # Check 2: Valid WAV header and duration
        try:
            with wave.open(wav_path, 'rb') as wf:
                n_channels = wf.getnchannels()
                sample_width = wf.getsampwidth()
                framerate = wf.getframerate()
                n_frames = wf.getnframes()
                
                if n_frames == 0:
                    return False, "WAV has zero frames"
                
                if framerate == 0:
                    return False, "WAV has invalid sample rate"
                
                duration = n_frames / framerate
                
                if duration < min_duration_sec:
                    return False, f"Duration too short ({duration:.2f}s < {min_duration_sec}s)"
        
        except wave.Error as e:
            return False, f"Invalid WAV format: {str(e)}"
        
        # Check 3: Audio is not silent
        rate, data = wavfile.read(wav_path)
        
        # Convert to float32
        if data.dtype == np.int16:
            data_float = data.astype(np.float32) / 32768.0
        elif data.dtype == np.int32:
            data_float = data.astype(np.float32) / 2147483648.0
        else:
            data_float = data.astype(np.float32)
        
        # Calculate RMS
        rms = np.sqrt(np.mean(data_float ** 2))
        
        if rms == 0:
            return False, "Audio is completely silent (RMS=0)"
        
        # Convert RMS to dB
        rms_db = 20 * np.log10(rms) if rms > 0 else -np.inf
        
        if rms_db < min_rms_db:
            return False, f"Audio too quiet (RMS={rms_db:.1f}dB < {min_rms_db}dB)"
        
        # All checks passed
        return True, None
        
    except Exception as e:
        return False, f"Validation error: {str(e)}"


def get_audio_stats(wav_path: str) -> dict:
    """
    Get detailed statistics about a WAV file
    
    Returns:
        Dict with: duration_sec, file_size_bytes, peak_amplitude, rms_db, is_valid
    """
    import os
    
    stats = {
        'file_exists': os.path.exists(wav_path),
        'file_size_bytes': 0,
        'duration_sec': 0.0,
        'sample_rate': 0,
        'channels': 0,
        'peak_amplitude': 0.0,
        'rms': 0.0,
        'rms_db': -np.inf,
        'is_valid': False,
        'error': None
    }
    
    if not os.path.exists(wav_path):
        stats['error'] = 'File does not exist'
        return stats
    
    try:
        # File size
        stats['file_size_bytes'] = os.path.getsize(wav_path)
        
        # WAV metadata
        with wave.open(wav_path, 'rb') as wf:
            stats['channels'] = wf.getnchannels()
            stats['sample_rate'] = wf.getframerate()
            n_frames = wf.getnframes()
            stats['duration_sec'] = n_frames / stats['sample_rate'] if stats['sample_rate'] > 0 else 0.0
        
        # Audio stats
        rate, data = wavfile.read(wav_path)
        
        if data.dtype == np.int16:
            data_float = data.astype(np.float32) / 32768.0
        elif data.dtype == np.int32:
            data_float = data.astype(np.float32) / 2147483648.0
        else:
            data_float = data.astype(np.float32)
        
        stats['peak_amplitude'] = float(np.abs(data_float).max())
        stats['rms'] = float(np.sqrt(np.mean(data_float ** 2)))
        stats['rms_db'] = float(20 * np.log10(stats['rms'])) if stats['rms'] > 0 else -np.inf
        
        # Validation
        is_valid, error = validate_audio_file(wav_path)
        stats['is_valid'] = is_valid
        stats['error'] = error
        
    except Exception as e:
        stats['error'] = str(e)
    
    return stats


def create_fallback_audio(output_path: str, duration_sec: float = 30.0, sample_rate: int = 44100):
    """
    Create a simple fallback audio file (safe beat) when generation fails
    
    This is a last resort to avoid returning a zero-length file.
    Creates a simple kick drum pattern at 120 BPM.
    
    Args:
        output_path: Where to write the fallback WAV
        duration_sec: Duration in seconds
        sample_rate: Sample rate (default: 44100)
    """
    print(f"[FALLBACK] Creating safe fallback audio: {duration_sec}s")
    
    # Generate simple kick drum at 120 BPM
    bpm = 120
    beat_interval = 60.0 / bpm  # seconds per beat
    
    # Create silent buffer
    total_samples = int(duration_sec * sample_rate)
    audio = np.zeros(total_samples, dtype=np.float32)
    
    # Add kick on every beat (quarter notes)
    # Simple exponential decay kick
    kick_duration = 0.2  # 200ms
    kick_samples = int(kick_duration * sample_rate)
    kick_freq = 60  # Hz (low kick)
    
    # Generate kick waveform
    t = np.linspace(0, kick_duration, kick_samples)
    kick = np.sin(2 * np.pi * kick_freq * t) * np.exp(-t * 15)  # Exponential decay
    
    # Place kicks on every beat
    current_time = 0.0
    while current_time < duration_sec:
        start_sample = int(current_time * sample_rate)
        end_sample = min(start_sample + kick_samples, total_samples)
        actual_length = end_sample - start_sample
        
        if actual_length > 0:
            audio[start_sample:end_sample] += kick[:actual_length]
        
        current_time += beat_interval
    
    # Normalize
    peak = np.abs(audio).max()
    if peak > 0:
        audio = audio * (0.8 / peak)
    
    # Convert to stereo
    audio_stereo = np.stack([audio, audio], axis=-1)
    
    # Save
    audio_int16 = (audio_stereo * 32767).astype(np.int16)
    wavfile.write(output_path, sample_rate, audio_int16)
    
    print(f"[FALLBACK] Fallback audio created: {output_path}")
