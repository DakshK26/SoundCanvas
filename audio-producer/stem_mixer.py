"""
Stem Mixer - Mix multiple instrument stems with sidechain compression
"""
import numpy as np
from scipy.io import wavfile
import os
from typing import List, Dict, Tuple, Optional


def load_wav(path: str) -> Tuple[int, np.ndarray]:
    """Load WAV file and return (sample_rate, audio_data)"""
    rate, data = wavfile.read(path)
    
    # Convert to float32
    if data.dtype == np.int16:
        data = data.astype(np.float32) / 32768.0
    elif data.dtype == np.int32:
        data = data.astype(np.float32) / 2147483648.0
    else:
        data = data.astype(np.float32)
    
    # Convert mono to stereo
    if len(data.shape) == 1:
        data = np.stack([data, data], axis=-1)
    
    return rate, data


def save_wav(path: str, rate: int, data: np.ndarray):
    """Save audio data as WAV file"""
    # Clip to prevent overflow
    data = np.clip(data, -1.0, 1.0)
    
    # Convert to int16
    data_int16 = (data * 32767).astype(np.int16)
    
    wavfile.write(path, rate, data_int16)


def create_kick_envelope(kick_wav: str, sample_rate: int, total_samples: int) -> np.ndarray:
    """
    Create sidechain envelope from kick drum pattern
    
    Args:
        kick_wav: Path to kick stem WAV
        sample_rate: Sample rate
        total_samples: Total length in samples
    
    Returns:
        Envelope array (1D) with sidechain ducking curve
    """
    try:
        rate, kick_data = load_wav(kick_wav)
        
        # Convert to mono for envelope detection
        if len(kick_data.shape) == 2:
            kick_mono = np.mean(kick_data, axis=1)
        else:
            kick_mono = kick_data
        
        # Resample if needed
        if rate != sample_rate:
            from scipy.signal import resample
            kick_mono = resample(kick_mono, int(len(kick_mono) * sample_rate / rate))
        
        # Detect kick hits (simple peak detection)
        # Take absolute value and smooth
        envelope = np.abs(kick_mono)
        
        # Expand envelope to match total samples
        if len(envelope) < total_samples:
            # Tile/repeat the kick pattern
            repeats = int(np.ceil(total_samples / len(envelope)))
            envelope = np.tile(envelope, repeats)[:total_samples]
        else:
            envelope = envelope[:total_samples]
        
        # Smooth envelope (attack/release)
        from scipy.ndimage import gaussian_filter1d
        envelope = gaussian_filter1d(envelope, sigma=sample_rate * 0.01)  # 10ms smoothing
        
        # Normalize to 0-1 range
        if envelope.max() > 0:
            envelope = envelope / envelope.max()
        
        # Create ducking curve: 1 - (envelope * depth)
        # When kick hits (envelope high), output is reduced
        sidechain_depth = 0.6  # 60% ducking on kick hits
        ducking_curve = 1.0 - (envelope * sidechain_depth)
        
        return ducking_curve
        
    except Exception as e:
        print(f"Kick envelope error: {str(e)}")
        # Return flat envelope (no ducking)
        return np.ones(total_samples)


def apply_sidechain(audio: np.ndarray, kick_envelope: np.ndarray) -> np.ndarray:
    """
    Apply sidechain compression using kick envelope
    
    Args:
        audio: Stereo audio data (N, 2)
        kick_envelope: 1D envelope array
    
    Returns:
        Sidechained audio
    """
    # Expand envelope to stereo
    if len(kick_envelope) != len(audio):
        # Truncate or pad
        if len(kick_envelope) > len(audio):
            kick_envelope = kick_envelope[:len(audio)]
        else:
            kick_envelope = np.pad(kick_envelope, (0, len(audio) - len(kick_envelope)), 'edge')
    
    envelope_stereo = np.stack([kick_envelope, kick_envelope], axis=-1)
    
    return audio * envelope_stereo


def mix_stems(stems: Dict[str, str], output_path: str, 
              apply_sidechain_to: List[str] = ['bass', 'lead', 'pad'],
              stem_gains: Optional[Dict[str, float]] = None) -> bool:
    """
    Mix multiple instrument stems with optional sidechain compression
    
    Args:
        stems: Dict mapping stem name -> WAV file path
                e.g., {'kick': '/data/stems/kick.wav', 'bass': '/data/stems/bass.wav'}
        output_path: Output mixed WAV path
        apply_sidechain_to: List of stem names to apply sidechain ducking
        stem_gains: Optional dict of gain multipliers per stem
    
    Returns:
        True if successful
    """
    try:
        if not stems:
            print("No stems to mix")
            return False
        
        # Default gains (EDM mixing guidelines)
        default_gains = {
            'kick': 1.0,      # Kick is reference (0dB)
            'snare': 0.8,     # Snare slightly lower
            'hihat': 0.5,     # Hats in background
            'bass': 0.9,      # Bass almost as loud as kick
            'lead': 0.7,      # Lead melody prominent but not overpowering
            'pad': 0.4,       # Pads create atmosphere
            'arp': 0.6,       # Arps mid-level
            'fx': 0.3,        # Effects subtle
        }
        
        if stem_gains:
            default_gains.update(stem_gains)
        
        # Load all stems
        loaded_stems = {}
        max_length = 0
        sample_rate = None
        
        for name, path in stems.items():
            if not os.path.exists(path):
                print(f"Stem not found: {path}")
                continue
            
            rate, data = load_wav(path)
            loaded_stems[name] = data
            
            if sample_rate is None:
                sample_rate = rate
            elif rate != sample_rate:
                # Resample if needed
                from scipy.signal import resample
                new_length = int(len(data) * sample_rate / rate)
                data = resample(data, new_length, axis=0)
                loaded_stems[name] = data
            
            max_length = max(max_length, len(data))
        
        if not loaded_stems:
            print("No valid stems loaded")
            return False
        
        # Create kick envelope for sidechain (if kick exists)
        kick_envelope = None
        if 'kick' in stems and os.path.exists(stems['kick']):
            kick_envelope = create_kick_envelope(stems['kick'], sample_rate, max_length)
        
        # Mix all stems
        mixed = np.zeros((max_length, 2), dtype=np.float32)
        
        for name, audio in loaded_stems.items():
            # Pad to max length
            if len(audio) < max_length:
                audio = np.pad(audio, ((0, max_length - len(audio)), (0, 0)), 'constant')
            
            # Apply gain
            gain = default_gains.get(name, 0.7)
            audio = audio * gain
            
            # Apply sidechain if requested and kick envelope exists
            if kick_envelope is not None and name in apply_sidechain_to:
                audio = apply_sidechain(audio, kick_envelope)
            
            # Add to mix
            mixed += audio
        
        # Normalize to prevent clipping (headroom for mastering)
        peak = np.abs(mixed).max()
        if peak > 0.8:  # Leave 0.2 headroom for mastering
            mixed = mixed * (0.8 / peak)
        
        # Save mixed output
        save_wav(output_path, sample_rate, mixed)
        
        return True
        
    except Exception as e:
        print(f"Stem mixing error: {str(e)}")
        return False


def mix_stems_simple(stem_paths: List[str], output_path: str, gains: Optional[List[float]] = None) -> bool:
    """
    Simple stem mixer without sidechain (fast path)
    
    Args:
        stem_paths: List of WAV file paths
        output_path: Output WAV path
        gains: Optional list of gain values (same order as stem_paths)
    
    Returns:
        True if successful
    """
    try:
        if not stem_paths:
            return False
        
        if gains is None:
            gains = [1.0 / len(stem_paths)] * len(stem_paths)  # Equal mix
        
        loaded = []
        sample_rate = None
        max_length = 0
        
        for path in stem_paths:
            if not os.path.exists(path):
                continue
            rate, data = load_wav(path)
            loaded.append(data)
            
            if sample_rate is None:
                sample_rate = rate
            
            max_length = max(max_length, len(data))
        
        if not loaded:
            return False
        
        # Mix
        mixed = np.zeros((max_length, 2), dtype=np.float32)
        
        for i, audio in enumerate(loaded):
            if len(audio) < max_length:
                audio = np.pad(audio, ((0, max_length - len(audio)), (0, 0)), 'constant')
            
            gain = gains[i] if i < len(gains) else 1.0
            mixed += audio * gain
        
        # Normalize
        peak = np.abs(mixed).max()
        if peak > 0.8:
            mixed = mixed * (0.8 / peak)
        
        save_wav(output_path, sample_rate, mixed)
        return True
        
    except Exception as e:
        print(f"Simple mixing error: {str(e)}")
        return False
