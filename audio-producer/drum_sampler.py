"""
Phase 9: Sample-based Drum Renderer
Renders drum MIDI using WAV samples from Freesound instead of FluidSynth

MUSICAL HUMANIZATION (v2):
- Groove templates: Genre-specific timing feel (not random jitter)
- Accent patterns: Velocity curves based on beat position
- Swing: Delayed offbeats for shuffle feel
- Ghost note handling: Very soft dynamics for subtlety
"""

import mido
import numpy as np
import soundfile as sf
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import random


class DrumSampler:
    """
    Renders drum MIDI tracks using WAV samples
    With musical humanization for authentic feel
    """
    
    # GENRE-SPECIFIC GROOVE TEMPLATES
    # Timing offset in ms for each 16th note position (0-15)
    GROOVE_TEMPLATES = {
        'trap_808': [0, -2, 0, 2, 0, -1, 0, 3, 0, -2, 0, 2, 0, -1, 0, 4],
        'house': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],  # Tight
        'rnb_soft': [0, 3, 2, 4, 2, 3, 2, 5, 0, 3, 2, 4, 2, 3, 2, 6],  # Laid back
        'default': [0, 1, 0, 2, 0, 1, 0, 2, 0, 1, 0, 2, 0, 1, 0, 3],
    }
    
    # ACCENT PATTERNS: Velocity multipliers per 16th note
    ACCENT_PATTERNS = {
        'trap_808': [1.0, 0.6, 0.8, 0.5, 0.9, 0.55, 0.75, 0.5, 1.0, 0.6, 0.8, 0.5, 0.9, 0.55, 0.75, 0.6],
        'house': [0.85, 0.7, 1.0, 0.65, 0.85, 0.7, 1.0, 0.65, 0.85, 0.7, 1.0, 0.65, 0.85, 0.7, 1.0, 0.75],
        'rnb_soft': [1.0, 0.4, 0.7, 0.35, 0.95, 0.4, 0.65, 0.35, 1.0, 0.4, 0.7, 0.35, 0.95, 0.4, 0.65, 0.4],
        'default': [1.0, 0.65, 0.85, 0.6, 0.95, 0.65, 0.8, 0.6, 1.0, 0.65, 0.85, 0.6, 0.95, 0.65, 0.8, 0.65],
    }
    
    # SWING AMOUNTS (0.0 = no swing, 0.3 = heavy shuffle)
    SWING_AMOUNTS = {
        'trap_808': 0.08,
        'house': 0.03,
        'rnb_soft': 0.22,
        'default': 0.05,
    }
    
    def __init__(self, kit_name: str, assets_dir: Optional[Path] = None, samplerate: int = 44100):
        """
        Initialize drum sampler
        
        Args:
            kit_name: Name of drum kit (e.g., 'trap_808', 'house', 'rnb_soft')
            assets_dir: Path to assets directory (defaults to audio-producer/assets/)
            samplerate: Target sample rate
        """
        self.kit_name = kit_name
        self.samplerate = samplerate
        
        if assets_dir is None:
            script_dir = Path(__file__).parent
            assets_dir = script_dir / 'assets'
        
        self.assets_dir = assets_dir
        self.kits_dir = assets_dir / 'kits'
        self.drums_dir = assets_dir / 'drums'
        
        # Load kit configuration
        kit_config_path = self.kits_dir / f'{kit_name}.yaml'
        if not kit_config_path.exists():
            raise FileNotFoundError(f"Kit config not found: {kit_config_path}")
        
        with open(kit_config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Parse MIDI note mapping
        self.midi_to_category = {}
        for midi_note_str, category in self.config.get('mapping', {}).items():
            self.midi_to_category[int(midi_note_str)] = category
        
        # Load sample pools for each category
        self.sample_pools = self._load_sample_pools()
        
        # Round-robin indices
        self.round_robin_idx = {cat: 0 for cat in self.sample_pools.keys()}
    
    def _load_sample_pools(self) -> Dict[str, List[Tuple[np.ndarray, int]]]:
        """
        Load all WAV samples for the kit
        
        Returns:
            Dict mapping category -> list of (audio_data, original_samplerate) tuples
        """
        kit_drum_dir = self.drums_dir / self.kit_name
        pools = {}
        
        if not kit_drum_dir.exists():
            print(f"Warning: No samples found for kit '{self.kit_name}' at {kit_drum_dir}")
            print(f"         Run tools/fetch_freesound_assets.py to download samples")
            return pools
        
        # Load samples for each category
        for category in self.config.get('tags', {}).keys():
            category_dir = kit_drum_dir / category
            
            if not category_dir.exists() or not any(category_dir.glob('*.wav')):
                print(f"  Warning: No samples for category '{category}' in kit '{self.kit_name}'")
                pools[category] = []
                continue
            
            samples = []
            for wav_file in sorted(category_dir.glob('*.wav')):
                try:
                    audio, sr = sf.read(wav_file)
                    # Convert to mono if stereo
                    if len(audio.shape) > 1:
                        audio = np.mean(audio, axis=1)
                    samples.append((audio, sr))
                except Exception as e:
                    print(f"  Warning: Failed to load {wav_file}: {e}")
            
            pools[category] = samples
            print(f"  Loaded {len(samples)} samples for category '{category}'")
        
        return pools
    
    def get_sample(self, midi_note: int, velocity: int, method: str = 'round-robin') -> Optional[np.ndarray]:
        """
        Get a sample for a MIDI note with velocity
        
        Args:
            midi_note: MIDI note number
            velocity: MIDI velocity (0-127)
            method: Sample selection method ('round-robin', 'random', 'velocity')
        
        Returns:
            Audio data resampled to target samplerate, or None if no sample available
        """
        # Map MIDI note to category
        category = self.midi_to_category.get(midi_note)
        if category is None:
            return None
        
        # Get sample pool for category
        pool = self.sample_pools.get(category, [])
        if not pool:
            return None
        
        # Select sample from pool
        if method == 'random':
            audio, original_sr = random.choice(pool)
        elif method == 'velocity':
            # Map velocity to sample index (higher velocity = later samples)
            idx = int((velocity / 127.0) * (len(pool) - 1))
            audio, original_sr = pool[idx]
        else:  # round-robin
            idx = self.round_robin_idx[category]
            audio, original_sr = pool[idx]
            self.round_robin_idx[category] = (idx + 1) % len(pool)
        
        # Resample if necessary
        if original_sr != self.samplerate:
            audio = self._resample(audio, original_sr, self.samplerate)
        
        # Apply velocity
        velocity_scale = velocity / 127.0
        audio = audio * velocity_scale
        
        return audio
    
    def _resample(self, audio: np.ndarray, original_sr: int, target_sr: int) -> np.ndarray:
        """
        Resample audio to target sample rate
        
        Args:
            audio: Input audio
            original_sr: Original sample rate
            target_sr: Target sample rate
        
        Returns:
            Resampled audio
        """
        from scipy import signal
        
        if original_sr == target_sr:
            return audio
        
        # Calculate resampling ratio
        ratio = target_sr / original_sr
        num_samples = int(len(audio) * ratio)
        
        # Resample using scipy
        resampled = signal.resample(audio, num_samples)
        return resampled
    
    def render_midi(self, midi_path: Path, output_path: Path, duration_seconds: Optional[float] = None):
        """
        Render a MIDI file to WAV using drum samples
        With musical humanization for authentic feel
        
        Args:
            midi_path: Path to input MIDI file
            output_path: Path to output WAV file
            duration_seconds: Optional fixed duration (auto-detect from MIDI if None)
        """
        # Convert to Path objects if strings were provided
        midi_path = Path(midi_path)
        output_path = Path(output_path)
        
        print(f"Rendering drums with kit '{self.kit_name}'...")
        
        # Load MIDI file
        midi = mido.MidiFile(midi_path)
        
        # Get tempo and time signature
        tempo = 500000  # Default 120 BPM (500000 microseconds per beat)
        ticks_per_beat = midi.ticks_per_beat
        
        for track in midi.tracks:
            for msg in track:
                if msg.type == 'set_tempo':
                    tempo = msg.tempo
                    break
        
        # Calculate timing constants
        tick_duration = (tempo / 1_000_000.0) / ticks_per_beat
        sixteenth_note_duration = (tempo / 1_000_000.0) / 4  # Duration of a 16th note
        
        # Get genre-specific humanization settings
        groove_template = self.GROOVE_TEMPLATES.get(self.kit_name, self.GROOVE_TEMPLATES['default'])
        accent_pattern = self.ACCENT_PATTERNS.get(self.kit_name, self.ACCENT_PATTERNS['default'])
        swing_amount = self.SWING_AMOUNTS.get(self.kit_name, self.SWING_AMOUNTS['default'])
        
        # Parse all note events from drum track (channel 9 = drums)
        note_events = []
        current_time = 0
        
        for track in midi.tracks:
            current_time = 0
            for msg in track:
                current_time += msg.time * tick_duration
                
                if msg.type == 'note_on' and msg.channel == 9 and msg.velocity > 0:
                    # Calculate 16th note position for humanization
                    bar_position_sec = current_time % (sixteenth_note_duration * 16)
                    sixteenth_position = int(bar_position_sec / sixteenth_note_duration) % 16
                    
                    # MUSICAL HUMANIZATION: Groove template timing
                    groove_offset_ms = groove_template[sixteenth_position]
                    timing_offset_sec = groove_offset_ms / 1000.0
                    
                    # Add minimal random jitter (±3ms)
                    timing_offset_sec += random.gauss(0, 0.003 / 2)
                    
                    # Apply swing to offbeat 8th notes (positions 2, 6, 10, 14)
                    if sixteenth_position in [2, 6, 10, 14]:
                        timing_offset_sec += swing_amount * sixteenth_note_duration
                    
                    humanized_time = max(0, current_time + timing_offset_sec)
                    
                    # MUSICAL HUMANIZATION: Accent pattern velocity
                    accent_mult = accent_pattern[sixteenth_position]
                    velocity = msg.velocity
                    
                    # Ghost notes (low velocity) stay quiet
                    if velocity < 50:
                        velocity = int(velocity * 0.7 * accent_mult)
                    else:
                        velocity = int(velocity * accent_mult)
                    
                    # Small random variation (±6%)
                    velocity = int(velocity * (1.0 + random.gauss(0, 0.06)))
                    velocity = max(20, min(127, velocity))
                    
                    note_events.append({
                        'time': humanized_time,
                        'note': msg.note,
                        'velocity': velocity
                    })
        
        # Determine output duration
        if duration_seconds is None:
            if note_events:
                duration_seconds = max(ev['time'] for ev in note_events) + 2.0
            else:
                duration_seconds = 10.0  # Default
        
        # Create output buffer
        num_samples = int(duration_seconds * self.samplerate)
        output = np.zeros(num_samples, dtype=np.float32)
        
        # Render each note event
        for event in note_events:
            sample = self.get_sample(event['note'], event['velocity'])
            if sample is not None:
                # Calculate sample position
                pos = int(event['time'] * self.samplerate)
                
                # Mix sample into output
                end_pos = min(pos + len(sample), num_samples)
                sample_len = end_pos - pos
                
                if sample_len > 0:
                    output[pos:end_pos] += sample[:sample_len]
        
        # Normalize to prevent clipping
        max_val = np.abs(output).max()
        if max_val > 0.95:
            output = output * (0.95 / max_val)
        
        # Save to file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(output_path, output, self.samplerate)
        
        print(f"  Wrote drum stem: {output_path}")
        print(f"  Duration: {duration_seconds:.2f}s, Events: {len(note_events)}")
        
        return output


def render_drums_from_midi(midi_path: Path, 
                           output_path: Path, 
                           kit_name: str = 'trap_808',
                           duration_seconds: Optional[float] = None) -> np.ndarray:
    """
    Convenience function to render drums from MIDI file
    
    Args:
        midi_path: Path to MIDI file
        output_path: Path to output WAV file
        kit_name: Name of drum kit to use
        duration_seconds: Optional fixed duration
    
    Returns:
        Rendered audio as numpy array
    """
    sampler = DrumSampler(kit_name)
    return sampler.render_midi(midi_path, output_path, duration_seconds)


if __name__ == '__main__':
    # Test the drum sampler
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python drum_sampler.py <midi_file> <output_wav> [kit_name]")
        sys.exit(1)
    
    midi_file = Path(sys.argv[1])
    output_file = Path(sys.argv[2])
    kit = sys.argv[3] if len(sys.argv) > 3 else 'trap_808'
    
    render_drums_from_midi(midi_file, output_file, kit)
    print("✓ Done")
