"""
Stem Mixer - Mix multiple instrument stems with sidechain compression
"""
import numpy as np
from scipy.io import wavfile
import os
from typing import List, Dict, Tuple, Optional
import mido


def parse_kick_events_from_midi(midi_path: str, tempo_bpm: float = 120.0) -> List[float]:
    """
    Phase 9: Parse kick drum events from MIDI file
    
    Args:
        midi_path: Path to MIDI file
        tempo_bpm: Tempo in BPM (if not found in MIDI)
    
    Returns:
        List of kick event times in seconds
    """
    try:
        midi = mido.MidiFile(midi_path)
        
        # Get tempo from MIDI
        tempo_microseconds = 500000  # Default 120 BPM
        for track in midi.tracks:
            for msg in track:
                if msg.type == 'set_tempo':
                    tempo_microseconds = msg.tempo
                    break
        
        # Convert to seconds per tick
        ticks_per_beat = midi.ticks_per_beat
        seconds_per_tick = (tempo_microseconds / 1_000_000.0) / ticks_per_beat
        
        # Parse kick events (MIDI note 35 and 36 on channel 9 = drums)
        kick_times = []
        
        for track in midi.tracks:
            current_time = 0.0
            for msg in track:
                current_time += msg.time * seconds_per_tick
                
                # Check for kick drum notes
                if (msg.type == 'note_on' and 
                    msg.channel == 9 and 
                    msg.note in [35, 36] and 
                    msg.velocity > 0):
                    kick_times.append(current_time)
        
        return kick_times
    
    except Exception as e:
        print(f"Warning: Failed to parse MIDI kicks: {e}")
        return []


def create_sidechain_envelope_from_midi(midi_path: str, 
                                        duration_seconds: float,
                                        sample_rate: int,
                                        sidechain_amount: float = 0.5,
                                        attack_ms: float = 5.0,
                                        hold_ms: float = 50.0,
                                        release_ms: float = 250.0) -> np.ndarray:
    """
    Phase 9: Create sidechain ducking envelope from MIDI kick events
    
    Args:
        midi_path: Path to MIDI file
        duration_seconds: Total duration of track
        sample_rate: Audio sample rate
        sidechain_amount: Amount of ducking (0-1)
        attack_ms: Attack time in milliseconds
        hold_ms: Hold time in milliseconds
        release_ms: Release time in milliseconds
    
    Returns:
        Envelope array (values 0-1) where kicks cause dips
    """
    # Parse kick events
    kick_times = parse_kick_events_from_midi(midi_path)
    
    if not kick_times:
        print("  No kick events found in MIDI, sidechain disabled")
        return np.ones(int(duration_seconds * sample_rate))
    
    print(f"  Found {len(kick_times)} kick events for sidechain")
    
    # Create envelope
    total_samples = int(duration_seconds * sample_rate)
    envelope = np.ones(total_samples)
    
    # Convert times to samples
    attack_samples = int((attack_ms / 1000.0) * sample_rate)
    hold_samples = int((hold_ms / 1000.0) * sample_rate)
    release_samples = int((release_ms / 1000.0) * sample_rate)
    
    # For each kick, create a ducking curve
    for kick_time in kick_times:
        start_sample = int(kick_time * sample_rate)
        
        if start_sample >= total_samples:
            continue
        
        # Attack phase: rapid duck down
        for i in range(attack_samples):
            sample_idx = start_sample + i
            if sample_idx >= total_samples:
                break
            
            # Linear ramp down
            duck_amount = (i / attack_samples) * sidechain_amount
            new_value = 1.0 - duck_amount
            
            # Take minimum (allow overlapping kicks to stack)
            envelope[sample_idx] = min(envelope[sample_idx], new_value)
        
        # Hold phase: stay ducked
        hold_start = start_sample + attack_samples
        for i in range(hold_samples):
            sample_idx = hold_start + i
            if sample_idx >= total_samples:
                break
            
            new_value = 1.0 - sidechain_amount
            envelope[sample_idx] = min(envelope[sample_idx], new_value)
        
        # Release phase: gradual return to normal
        release_start = hold_start + hold_samples
        for i in range(release_samples):
            sample_idx = release_start + i
            if sample_idx >= total_samples:
                break
            
            # Exponential release curve
            progress = i / release_samples
            duck_amount = sidechain_amount * (1.0 - progress)
            new_value = 1.0 - duck_amount
            
            envelope[sample_idx] = min(envelope[sample_idx], new_value)
    
    return envelope


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
              stem_gains: Optional[Dict[str, float]] = None,
              midi_path: Optional[str] = None,
              sidechain_amount: float = 0.5) -> bool:
    """
    Mix multiple instrument stems with optional sidechain compression
    
    Phase 9: Added MIDI-based sidechain for precise kick timing
    
    Args:
        stems: Dict mapping stem name -> WAV file path
                e.g., {'kick': '/data/stems/kick.wav', 'bass': '/data/stems/bass.wav'}
        output_path: Output mixed WAV path
        apply_sidechain_to: List of stem names to apply sidechain ducking
        stem_gains: Optional dict of gain multipliers per stem
        midi_path: Optional path to MIDI file for precise kick timing sidechain
        sidechain_amount: Amount of sidechain ducking (0-1), from mix preset
    
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
        
        # Phase 9: Create sidechain envelope from MIDI kick events (preferred)
        # Fallback to audio-based envelope if MIDI not available
        kick_envelope = None
        
        if midi_path and os.path.exists(midi_path):
            print(f"Creating sidechain from MIDI: {midi_path}")
            duration_seconds = max_length / sample_rate
            kick_envelope = create_sidechain_envelope_from_midi(
                midi_path, 
                duration_seconds, 
                sample_rate,
                sidechain_amount=sidechain_amount
            )
        elif 'kick' in stems and os.path.exists(stems['kick']):
            print("Creating sidechain from kick audio (fallback)")
            kick_envelope = create_kick_envelope(stems['kick'], sample_rate, max_length)
        else:
            print("No MIDI or kick stem found, sidechain disabled")
        
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


# End of stem_mixer.py
