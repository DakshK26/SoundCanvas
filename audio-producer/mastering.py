"""
Mastering Chain - EQ, Compression, Limiting
Targets -14 LUFS for consistent loudness
"""
import subprocess
import os
import tempfile
import numpy as np
from scipy.io import wavfile


def apply_mastering_chain(input_wav: str, output_wav: str, target_lufs: float = -14.0) -> bool:
    """
    Apply mastering chain using ffmpeg audio filters:
    1. EQ - boost lows, control mids, brighten highs
    2. Compressor - control dynamics
    3. Limiter - prevent clipping and hit target loudness
    
    Args:
        input_wav: Path to input WAV file
        output_wav: Path to output WAV file
        target_lufs: Target loudness in LUFS (default: -14.0)
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Multi-stage mastering chain
        temp_eq = tempfile.NamedTemporaryFile(suffix='.wav', delete=False).name
        temp_comp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False).name
        
        # Stage 1: EQ
        # - Low shelf: +3dB at 100Hz (EDM bass punch)
        # - Mid scoop: -2dB at 500Hz (clear out mud)
        # - High shelf: +2dB at 8000Hz (air/brightness)
        eq_filter = (
            "equalizer=f=100:t=h:width=200:g=3,"      # Bass boost
            "equalizer=f=500:t=h:width=400:g=-2,"     # Mid scoop
            "equalizer=f=8000:t=h:width=2000:g=2"     # High boost
        )
        
        eq_cmd = [
            'ffmpeg', '-y', '-i', input_wav,
            '-af', eq_filter,
            '-ar', '44100', '-ac', '2',
            temp_eq
        ]
        
        subprocess.run(eq_cmd, check=True, capture_output=True)
        
        # Stage 2: Compression
        # - Ratio 4:1 (moderate EDM compression)
        # - Threshold -18dB
        # - Attack 5ms (let transients through)
        # - Release 50ms (pump feel)
        # - Makeup gain 6dB
        comp_filter = (
            "acompressor="
            "threshold=-18dB:"
            "ratio=4:"
            "attack=5:"
            "release=50:"
            "makeup=6dB"
        )
        
        comp_cmd = [
            'ffmpeg', '-y', '-i', temp_eq,
            '-af', comp_filter,
            '-ar', '44100', '-ac', '2',
            temp_comp
        ]
        
        subprocess.run(comp_cmd, check=True, capture_output=True)
        
        # Stage 3: Limiting + Loudness normalization
        # - Limit at -0.1dB (prevent clipping)
        # - Normalize to target LUFS
        limiter_filter = (
            f"loudnorm=I={target_lufs}:LRA=7:tp=-0.1,"  # Loudness normalization
            "alimiter=limit=0.99:attack=1:release=50"    # Final limiter
        )
        
        final_cmd = [
            'ffmpeg', '-y', '-i', temp_comp,
            '-af', limiter_filter,
            '-ar', '44100', '-ac', '2',
            output_wav
        ]
        
        subprocess.run(final_cmd, check=True, capture_output=True)
        
        # Cleanup temp files
        os.remove(temp_eq)
        os.remove(temp_comp)
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"Mastering error: {e.stderr.decode() if e.stderr else str(e)}")
        # Cleanup temp files on error
        if os.path.exists(temp_eq):
            os.remove(temp_eq)
        if os.path.exists(temp_comp):
            os.remove(temp_comp)
        return False
    except Exception as e:
        print(f"Mastering error: {str(e)}")
        return False


def measure_lufs(wav_path: str) -> float:
    """
    Measure integrated LUFS of a WAV file
    
    Args:
        wav_path: Path to WAV file
    
    Returns:
        LUFS value (float), or -70.0 on error
    """
    try:
        cmd = [
            'ffmpeg', '-i', wav_path,
            '-af', 'loudnorm=print_format=json',
            '-f', 'null', '-'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        output = result.stderr
        
        # Parse JSON output from loudnorm filter
        import json
        json_start = output.find('{')
        json_end = output.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            loudness_data = json.loads(output[json_start:json_end])
            return float(loudness_data.get('input_i', -70.0))
        
        return -70.0
        
    except Exception as e:
        print(f"LUFS measurement error: {str(e)}")
        return -70.0


def apply_simple_limiter(input_wav: str, output_wav: str, ceiling_db: float = -0.1) -> bool:
    """
    Apply simple limiter (fast path without full mastering)
    
    Args:
        input_wav: Path to input WAV
        output_wav: Path to output WAV
        ceiling_db: Peak ceiling in dB
    
    Returns:
        True if successful
    """
    try:
        cmd = [
            'ffmpeg', '-y', '-i', input_wav,
            '-af', f'alimiter=limit=0.99:attack=1:release=50',
            '-ar', '44100', '-ac', '2',
            output_wav
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        return True
        
    except Exception as e:
        print(f"Limiter error: {str(e)}")
        return False
