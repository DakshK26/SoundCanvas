"""
Phase 9: FX Player - Play transition effects (risers, downlifters, impacts)
Uses Freesound samples + procedural fallbacks
"""
import numpy as np
import soundfile as sf
from scipy import signal
from typing import List, Dict, Optional, Tuple
import os
import random
import yaml


class FXPlayer:
    """Phase 9: Plays FX samples at section boundaries"""
    
    def __init__(self, fx_config_path: str, assets_dir: str, sample_rate: int = 44100):
        """
        Args:
            fx_config_path: Path to fx_config.yaml
            assets_dir: Directory where downloaded FX samples are stored
            sample_rate: Target sample rate
        """
        self.sample_rate = sample_rate
        self.assets_dir = assets_dir
        
        # Load FX config
        with open(fx_config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Cache loaded samples
        self.sample_cache: Dict[str, List[np.ndarray]] = {
            'uplifters': [],
            'downlifters': [],
            'impacts': []
        }
        
        self._load_samples()
    
    def _load_samples(self):
        """Load all available FX samples into cache"""
        for fx_type in ['uplifters', 'downlifters', 'impacts']:
            fx_dir = os.path.join(self.assets_dir, 'fx', fx_type)
            
            if not os.path.exists(fx_dir):
                print(f"  FX directory not found: {fx_dir}, will use procedural FX")
                continue
            
            # Load all WAV/OGG files
            for filename in os.listdir(fx_dir):
                if filename.endswith(('.wav', '.ogg', '.flac')):
                    filepath = os.path.join(fx_dir, filename)
                    try:
                        audio, sr = sf.read(filepath)
                        
                        # Convert to stereo if mono
                        if len(audio.shape) == 1:
                            audio = np.stack([audio, audio], axis=1)
                        
                        # Resample if needed
                        if sr != self.sample_rate:
                            from scipy.signal import resample
                            new_length = int(len(audio) * self.sample_rate / sr)
                            audio = resample(audio, new_length, axis=0)
                        
                        self.sample_cache[fx_type].append(audio.astype(np.float32))
                        
                    except Exception as e:
                        print(f"  Warning: Failed to load FX sample {filename}: {e}")
            
            print(f"  Loaded {len(self.sample_cache[fx_type])} {fx_type} samples")
    
    def generate_uplifter(self, duration: float, frequency_range: Tuple[float, float] = (200, 8000)) -> np.ndarray:
        """
        Procedural uplifter/riser (white noise filtered sweep)
        
        Args:
            duration: Duration in seconds
            frequency_range: (start_freq, end_freq) in Hz
        
        Returns:
            Stereo audio array
        """
        num_samples = int(duration * self.sample_rate)
        
        # White noise
        noise = np.random.randn(num_samples).astype(np.float32)
        
        # Create sweeping filter
        start_freq, end_freq = frequency_range
        
        # Exponential frequency sweep
        freqs = np.logspace(np.log10(start_freq), np.log10(end_freq), num_samples)
        
        # Apply bandpass filter that sweeps
        filtered = np.zeros(num_samples, dtype=np.float32)
        
        # Simple filtering approach: split into chunks and filter each
        chunk_size = 2048
        for i in range(0, num_samples, chunk_size):
            end_idx = min(i + chunk_size, num_samples)
            chunk = noise[i:end_idx]
            
            # Get center frequency for this chunk
            center_freq = freqs[i]
            
            # Bandpass filter (normalized frequencies)
            nyquist = self.sample_rate / 2
            low = max(center_freq * 0.8, 20) / nyquist
            high = min(center_freq * 1.2, nyquist - 100) / nyquist
            
            if low < high and low > 0 and high < 1:
                try:
                    sos = signal.butter(4, [low, high], btype='band', output='sos')
                    chunk_filtered = signal.sosfilt(sos, chunk)
                    filtered[i:end_idx] = chunk_filtered
                except:
                    filtered[i:end_idx] = chunk * 0.1  # Fallback
        
        # Apply amplitude envelope (exponential rise)
        envelope = np.linspace(0, 1, num_samples) ** 2
        filtered = filtered * envelope
        
        # Normalize
        peak = np.abs(filtered).max()
        if peak > 0:
            filtered = filtered * (0.7 / peak)
        
        # Convert to stereo
        stereo = np.stack([filtered, filtered], axis=1)
        
        return stereo
    
    def generate_downlifter(self, duration: float, frequency_range: Tuple[float, float] = (8000, 200)) -> np.ndarray:
        """
        Procedural downlifter (reverse sweep)
        
        Args:
            duration: Duration in seconds
            frequency_range: (start_freq, end_freq) in Hz
        
        Returns:
            Stereo audio array
        """
        # Just reverse the frequency range of uplifter
        return self.generate_uplifter(duration, frequency_range)
    
    def generate_impact(self, duration: float = 0.5) -> np.ndarray:
        """
        Procedural impact (kick-like transient)
        
        Args:
            duration: Duration in seconds
        
        Returns:
            Stereo audio array
        """
        num_samples = int(duration * self.sample_rate)
        
        # Sine wave with pitch drop
        start_freq = 150
        end_freq = 40
        
        # Exponential frequency envelope
        phase = 0
        signal_out = np.zeros(num_samples, dtype=np.float32)
        
        for i in range(num_samples):
            progress = i / num_samples
            freq = start_freq * (end_freq / start_freq) ** progress
            phase += 2 * np.pi * freq / self.sample_rate
            signal_out[i] = np.sin(phase)
        
        # Exponential decay envelope
        envelope = np.exp(-5 * np.linspace(0, 1, num_samples))
        signal_out = signal_out * envelope
        
        # Add some noise for texture
        noise = np.random.randn(num_samples) * 0.1
        noise = noise * np.exp(-10 * np.linspace(0, 1, num_samples))
        signal_out = signal_out * 0.9 + noise * 0.1
        
        # Normalize
        peak = np.abs(signal_out).max()
        if peak > 0:
            signal_out = signal_out * (0.8 / peak)
        
        # Convert to stereo
        stereo = np.stack([signal_out, signal_out], axis=1)
        
        return stereo
    
    def get_fx(self, fx_type: str, duration: float) -> np.ndarray:
        """
        Get FX sound (sample or procedural)
        
        Args:
            fx_type: 'uplifter', 'downlifter', or 'impact'
            duration: Desired duration in seconds
        
        Returns:
            Stereo audio array
        """
        # Try to use sample first
        if self.sample_cache[fx_type + 's']:  # Config uses plural
            sample = random.choice(self.sample_cache[fx_type + 's'])
            
            # Stretch/trim to match duration
            target_length = int(duration * self.sample_rate)
            
            if len(sample) > target_length:
                # Trim
                sample = sample[:target_length]
            elif len(sample) < target_length:
                # Stretch (simple time-stretch via resampling)
                from scipy.signal import resample
                sample = resample(sample, target_length, axis=0)
            
            return sample
        
        # Fallback to procedural
        if fx_type == 'uplifter':
            return self.generate_uplifter(duration)
        elif fx_type == 'downlifter':
            return self.generate_downlifter(duration)
        elif fx_type == 'impact':
            return self.generate_impact(duration)
        else:
            # Unknown type, return silence
            return np.zeros((int(duration * self.sample_rate), 2), dtype=np.float32)
    
    def render_fx_stem(self, 
                       midi_path: str, 
                       output_path: str,
                       total_duration: float,
                       fx_events: Optional[List[Dict]] = None) -> bool:
        """
        Render FX stem with effects at section boundaries
        
        Args:
            midi_path: Path to MIDI file (for parsing section metadata)
            output_path: Output WAV path
            total_duration: Total track duration in seconds
            fx_events: Optional list of FX events with format:
                       [{'time': 15.5, 'type': 'uplifter', 'duration': 2.0}, ...]
                       If None, will try to parse from MIDI metadata
        
        Returns:
            True if successful
        """
        try:
            # Create empty audio buffer
            total_samples = int(total_duration * self.sample_rate)
            fx_stem = np.zeros((total_samples, 2), dtype=np.float32)
            
            # If no events provided, try to parse from MIDI
            if fx_events is None:
                fx_events = self._parse_fx_events_from_midi(midi_path)
            
            if not fx_events:
                print("  No FX events found, creating empty FX stem")
            else:
                print(f"  Rendering {len(fx_events)} FX events")
            
            # Render each FX event
            for event in fx_events:
                fx_type = event.get('type', 'uplifter')
                time = event.get('time', 0)
                duration = event.get('duration', 2.0)
                
                # Get FX audio
                fx_audio = self.get_fx(fx_type, duration)
                
                # Place in timeline
                start_sample = int(time * self.sample_rate)
                end_sample = min(start_sample + len(fx_audio), total_samples)
                
                if start_sample < total_samples:
                    copy_length = end_sample - start_sample
                    fx_stem[start_sample:end_sample] += fx_audio[:copy_length]
            
            # Normalize
            peak = np.abs(fx_stem).max()
            if peak > 0.8:
                fx_stem = fx_stem * (0.8 / peak)
            
            # Save
            sf.write(output_path, fx_stem, self.sample_rate)
            
            return True
            
        except Exception as e:
            print(f"FX rendering error: {e}")
            return False
    
    def _parse_fx_events_from_midi(self, midi_path: str) -> List[Dict]:
        """
        Parse FX events from MIDI file metadata
        
        This is a simple heuristic: place uplifters before drops/builds,
        impacts at section starts
        
        Args:
            midi_path: Path to MIDI file
        
        Returns:
            List of FX events
        """
        try:
            import mido
            
            midi = mido.MidiFile(midi_path)
            
            # Get tempo
            tempo_microseconds = 500000  # Default 120 BPM
            for track in midi.tracks:
                for msg in track:
                    if msg.type == 'set_tempo':
                        tempo_microseconds = msg.tempo
                        break
            
            ticks_per_beat = midi.ticks_per_beat
            seconds_per_tick = (tempo_microseconds / 1_000_000.0) / ticks_per_beat
            
            # Find marker events (text/marker messages)
            events = []
            
            for track in midi.tracks:
                current_time = 0.0
                
                for msg in track:
                    current_time += msg.time * seconds_per_tick
                    
                    # Look for text/marker events
                    if msg.type in ['text', 'marker']:
                        text = msg.text.lower()
                        
                        # Parse section markers
                        if 'drop' in text or 'build' in text:
                            # Add uplifter before drop/build
                            events.append({
                                'time': max(0, current_time - 2.0),
                                'type': 'uplifter',
                                'duration': 2.0
                            })
                        
                        if 'break' in text or 'breakdown' in text:
                            # Add downlifter at breakdown
                            events.append({
                                'time': current_time,
                                'type': 'downlifter',
                                'duration': 1.5
                            })
                        
                        if 'intro' in text or 'verse' in text or 'chorus' in text:
                            # Add subtle impact at section start
                            events.append({
                                'time': current_time,
                                'type': 'impact',
                                'duration': 0.5
                            })
            
            # If no markers found, create simple heuristic based on time
            if not events:
                # Assume 4-bar sections at 120 BPM (8 seconds)
                # Place impacts every 16 seconds (typical section length)
                duration = midi.length if hasattr(midi, 'length') else 120.0
                
                for i in range(1, int(duration / 16)):
                    time = i * 16.0
                    events.append({
                        'time': time,
                        'type': 'impact',
                        'duration': 0.5
                    })
            
            return events
            
        except Exception as e:
            print(f"  Warning: Failed to parse FX events from MIDI: {e}")
            return []


# Test function
if __name__ == '__main__':
    print("Testing FX Player...")
    
    # Test procedural generation
    player = FXPlayer(
        fx_config_path='assets/fx/fx_config.yaml',
        assets_dir='assets',
        sample_rate=44100
    )
    
    print("Generating uplifter...")
    uplifter = player.generate_uplifter(2.0)
    print(f"  Shape: {uplifter.shape}")
    
    print("Generating downlifter...")
    downlifter = player.generate_downlifter(1.5)
    print(f"  Shape: {downlifter.shape}")
    
    print("Generating impact...")
    impact = player.generate_impact(0.5)
    print(f"  Shape: {impact.shape}")
    
    print("FX Player test complete!")
