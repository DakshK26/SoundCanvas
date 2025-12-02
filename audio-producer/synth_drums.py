"""
Synthesized Drum Generator - Clean Electronic Drums
Creates high-quality drums using synthesis with variation based on 7D image features.

Each genre has its own distinctive drum character:
- HOUSE: Punchy 4-on-floor kick, crisp claps, clean hats
- EDM_CHILL: Soft rounded kick, gentle snare, smooth hats  
- EDM_DROP: Hard-hitting kick, aggressive snare, bright hats
- CINEMATIC: Deep boomy kick, dramatic snare, subtle percussion

The 7D image vector (brightness, saturation, hue, contrast, colorfulness, 
sharpness, entropy) modulates:
- Kick pitch and decay
- Snare tone and noise mix
- Hi-hat brightness and decay
- Overall dynamics and groove tightness
"""

import numpy as np
from scipy import signal
from typing import Dict, Optional
import soundfile as sf
from pathlib import Path
import random


class DrumSynthesizer:
    """
    Synthesizes proper electronic drum sounds.
    Uses the 7D image feature vector for per-song variation.
    """
    
    def __init__(self, samplerate: int = 44100):
        self.sr = samplerate
        
        # Default 7D features (will be overwritten if provided)
        self.features = {
            'brightness': 0.5,
            'saturation': 0.5,
            'hue': 0.5,
            'contrast': 0.5,
            'colorfulness': 0.5,
            'sharpness': 0.5,
            'entropy': 0.5,
        }
    
    def set_image_features(self, features: Dict[str, float]):
        """Set image features for drum sound variation"""
        self.features = features
    
    def _vary(self, base: float, amount: float = 0.1) -> float:
        """Add small random variation"""
        return base * (1 + random.uniform(-amount, amount))
    
    # =========================================================================
    # KICK DRUMS - Clean, punchy, genre-appropriate
    # =========================================================================
    
    def synthesize_kick_house(self) -> np.ndarray:
        """
        House kick: Tight, punchy, 4-on-floor ready.
        Clean sine-based with sharp attack and controlled decay.
        """
        duration = 0.4
        t = np.linspace(0, duration, int(self.sr * duration))
        
        # Base pitch influenced by image brightness (brighter = higher pitch)
        base_pitch = 55 + self.features.get('brightness', 0.5) * 15  # 55-70 Hz
        
        # Pitch envelope - drops from higher frequency for click
        pitch_env = base_pitch * (1 + 4 * np.exp(-t * 40))  # Fast pitch drop
        
        # Generate clean sine wave kick body
        phase = np.cumsum(2 * np.pi * pitch_env / self.sr)
        kick = np.sin(phase)
        
        # Add subtle second harmonic for warmth (not brightness)
        kick += 0.2 * np.sin(2 * phase) * np.exp(-t * 20)
        
        # Sharp attack transient (click)
        click = np.exp(-t * 150) * 0.3
        
        # Amplitude envelope - tight decay
        decay_time = 0.15 + self.features.get('contrast', 0.5) * 0.1
        amp_env = np.exp(-t / decay_time)
        
        # Combine
        kick = kick * amp_env + click
        kick = np.tanh(kick * 1.3)  # Soft saturation for warmth
        kick = kick / np.max(np.abs(kick)) * 0.95
        
        return kick.astype(np.float32)
    
    def synthesize_kick_chill(self) -> np.ndarray:
        """
        Chill kick: Softer, rounder, less aggressive.
        Lower pitch, longer decay, smooth attack.
        """
        duration = 0.5
        t = np.linspace(0, duration, int(self.sr * duration))
        
        # Lower base pitch for warmth
        base_pitch = 45 + self.features.get('brightness', 0.5) * 10  # 45-55 Hz
        
        # Gentler pitch envelope
        pitch_env = base_pitch * (1 + 2 * np.exp(-t * 25))
        
        phase = np.cumsum(2 * np.pi * pitch_env / self.sr)
        kick = np.sin(phase)
        
        # More harmonics for fullness
        kick += 0.15 * np.sin(2 * phase) * np.exp(-t * 15)
        
        # Softer click
        click = np.exp(-t * 80) * 0.15
        
        # Longer decay
        decay_time = 0.25 + self.features.get('entropy', 0.5) * 0.1
        amp_env = np.exp(-t / decay_time)
        
        kick = kick * amp_env + click
        kick = np.tanh(kick * 1.1)
        kick = kick / np.max(np.abs(kick)) * 0.9
        
        return kick.astype(np.float32)
    
    def synthesize_kick_drop(self) -> np.ndarray:
        """
        EDM Drop kick: Hard-hitting, aggressive, cuts through.
        Higher pitch, fast decay, strong transient.
        """
        duration = 0.35
        t = np.linspace(0, duration, int(self.sr * duration))
        
        # Higher, more aggressive pitch
        base_pitch = 60 + self.features.get('saturation', 0.5) * 15  # 60-75 Hz
        
        # Very aggressive pitch drop
        pitch_env = base_pitch * (1 + 6 * np.exp(-t * 50))
        
        phase = np.cumsum(2 * np.pi * pitch_env / self.sr)
        kick = np.sin(phase)
        
        # Add distortion harmonics
        kick += 0.3 * np.sin(2 * phase) * np.exp(-t * 30)
        kick += 0.1 * np.sin(3 * phase) * np.exp(-t * 40)
        
        # Strong click transient
        click = np.exp(-t * 200) * 0.5
        
        # Fast decay
        decay_time = 0.12 + self.features.get('sharpness', 0.5) * 0.05
        amp_env = np.exp(-t / decay_time)
        
        kick = kick * amp_env + click
        kick = np.tanh(kick * 1.8)  # Heavy saturation
        kick = kick / np.max(np.abs(kick)) * 0.98
        
        return kick.astype(np.float32)
    
    def synthesize_kick_cinematic(self) -> np.ndarray:
        """
        Cinematic kick: Deep, boomy, dramatic.
        Very low pitch, long tail, subtle attack.
        """
        duration = 0.8
        t = np.linspace(0, duration, int(self.sr * duration))
        
        # Very low pitch for drama
        base_pitch = 35 + self.features.get('brightness', 0.5) * 10  # 35-45 Hz
        
        # Slow pitch envelope
        pitch_env = base_pitch * (1 + 1.5 * np.exp(-t * 15))
        
        phase = np.cumsum(2 * np.pi * pitch_env / self.sr)
        kick = np.sin(phase)
        
        # Subtle harmonics
        kick += 0.1 * np.sin(2 * phase) * np.exp(-t * 10)
        
        # Very soft click (or none for timpani-like feel)
        click = np.exp(-t * 60) * 0.1
        
        # Long, dramatic decay
        decay_time = 0.4 + self.features.get('entropy', 0.5) * 0.2
        amp_env = np.exp(-t / decay_time)
        
        kick = kick * amp_env + click
        kick = np.tanh(kick * 0.9)  # Minimal saturation
        kick = kick / np.max(np.abs(kick)) * 0.85
        
        return kick.astype(np.float32)
    
    # =========================================================================
    # SNARES - Clean electronic snares, not metallic
    # =========================================================================
    
    def synthesize_snare_house(self) -> np.ndarray:
        """
        House snare: Tight, punchy, crisp.
        Good balance of tone and noise.
        """
        duration = 0.2
        t = np.linspace(0, duration, int(self.sr * duration))
        
        # Tonal body (tuned membrane)
        tone_freq = 180 + self.features.get('saturation', 0.5) * 40
        tone = np.sin(2 * np.pi * tone_freq * t)
        tone += 0.3 * np.sin(2 * np.pi * tone_freq * 1.5 * t)  # Overtone
        tone_env = np.exp(-t / 0.08)
        tonal = tone * tone_env
        
        # Noise body (snare wires) - bandpassed for realism
        noise = np.random.randn(len(t))
        # Band-pass 1000-8000 Hz for snare character
        sos = signal.butter(3, [1000, 8000], 'band', fs=self.sr, output='sos')
        noise = signal.sosfilt(sos, noise)
        noise_env = np.exp(-t / 0.1)
        noise_out = noise * noise_env
        
        # Click transient
        click = np.exp(-t * 200) * 0.3
        
        # Mix: House snares are fairly balanced
        snare = 0.4 * tonal + 0.5 * noise_out + click
        snare = np.tanh(snare * 2)
        snare = snare / np.max(np.abs(snare)) * 0.8
        
        return snare.astype(np.float32)
    
    def synthesize_snare_chill(self) -> np.ndarray:
        """
        Chill snare: Softer, warmer, less aggressive.
        More tone, less bright noise.
        """
        duration = 0.25
        t = np.linspace(0, duration, int(self.sr * duration))
        
        # Lower, warmer tone
        tone_freq = 150 + self.features.get('brightness', 0.5) * 30
        tone = np.sin(2 * np.pi * tone_freq * t)
        tone += 0.4 * np.sin(2 * np.pi * tone_freq * 1.4 * t)
        tone_env = np.exp(-t / 0.12)
        tonal = tone * tone_env
        
        # Softer noise - lower frequency content
        noise = np.random.randn(len(t))
        sos = signal.butter(3, [800, 5000], 'band', fs=self.sr, output='sos')
        noise = signal.sosfilt(sos, noise)
        noise_env = np.exp(-t / 0.15)
        noise_out = noise * noise_env
        
        # Soft click
        click = np.exp(-t * 100) * 0.15
        
        # More tonal, less noise
        snare = 0.5 * tonal + 0.3 * noise_out + click
        snare = np.tanh(snare * 1.5)
        snare = snare / np.max(np.abs(snare)) * 0.7
        
        return snare.astype(np.float32)
    
    def synthesize_snare_drop(self) -> np.ndarray:
        """
        EDM Drop snare: Aggressive, bright, cutting.
        Heavy noise, strong transient.
        """
        duration = 0.18
        t = np.linspace(0, duration, int(self.sr * duration))
        
        # Higher, aggressive tone
        tone_freq = 200 + self.features.get('sharpness', 0.5) * 50
        tone = np.sin(2 * np.pi * tone_freq * t)
        tone += 0.2 * np.sin(2 * np.pi * tone_freq * 2 * t)
        tone_env = np.exp(-t / 0.06)
        tonal = tone * tone_env
        
        # Bright, aggressive noise
        noise = np.random.randn(len(t))
        sos = signal.butter(3, [2000, 12000], 'band', fs=self.sr, output='sos')
        noise = signal.sosfilt(sos, noise)
        noise_env = np.exp(-t / 0.08)
        noise_out = noise * noise_env
        
        # Strong transient
        click = np.exp(-t * 300) * 0.5
        
        # More noise, aggressive
        snare = 0.3 * tonal + 0.6 * noise_out + click
        snare = np.tanh(snare * 2.5)
        snare = snare / np.max(np.abs(snare)) * 0.9
        
        return snare.astype(np.float32)
    
    def synthesize_snare_cinematic(self) -> np.ndarray:
        """
        Cinematic snare: Dramatic, roomy, orchestral feel.
        More tone and reverb-like tail.
        """
        duration = 0.35
        t = np.linspace(0, duration, int(self.sr * duration))
        
        # Deep, dramatic tone
        tone_freq = 160 + self.features.get('contrast', 0.5) * 30
        tone = np.sin(2 * np.pi * tone_freq * t)
        tone += 0.5 * np.sin(2 * np.pi * tone_freq * 1.3 * t)
        tone_env = np.exp(-t / 0.15)
        tonal = tone * tone_env
        
        # Warmer noise
        noise = np.random.randn(len(t))
        sos = signal.butter(3, [600, 6000], 'band', fs=self.sr, output='sos')
        noise = signal.sosfilt(sos, noise)
        noise_env = np.exp(-t / 0.2)
        noise_out = noise * noise_env
        
        # Subtle click
        click = np.exp(-t * 80) * 0.2
        
        # Balanced but with longer tail
        snare = 0.5 * tonal + 0.4 * noise_out + click
        snare = np.tanh(snare * 1.3)
        snare = snare / np.max(np.abs(snare)) * 0.75
        
        return snare.astype(np.float32)
    
    # =========================================================================
    # HI-HATS - Clean, no metallic screech
    # =========================================================================
    
    def synthesize_hihat_closed(self, genre: str = 'house') -> np.ndarray:
        """
        Closed hi-hat: Short, tight, clean.
        Uses filtered noise, NOT metallic resonant peaks.
        """
        duration = 0.06 if genre in ['house', 'edmdrop'] else 0.08
        t = np.linspace(0, duration, int(self.sr * duration))
        
        # Pure noise base - no metallic resonances!
        hat = np.random.randn(len(t))
        
        # High-pass filter for brightness (not band-pass with resonance)
        hp_freq = 6000 + self.features.get('brightness', 0.5) * 4000  # 6k-10k
        hp_freq = min(hp_freq, self.sr / 2 - 100)
        sos_hp = signal.butter(2, hp_freq, 'high', fs=self.sr, output='sos')
        hat = signal.sosfilt(sos_hp, hat)
        
        # Sharp envelope for tightness
        decay = 0.02 + (1 - self.features.get('sharpness', 0.5)) * 0.02
        env = np.exp(-t / decay)
        
        # Quick attack
        attack = np.minimum(t * 500, 1.0)
        
        hat = hat * env * attack
        hat = hat / np.max(np.abs(hat)) * 0.5
        
        return hat.astype(np.float32)
    
    def synthesize_hihat_open(self, genre: str = 'house') -> np.ndarray:
        """
        Open hi-hat: Longer, ringing, clean.
        """
        duration = 0.2 if genre in ['house', 'edmdrop'] else 0.25
        t = np.linspace(0, duration, int(self.sr * duration))
        
        # Noise base
        hat = np.random.randn(len(t))
        
        # High-pass for brightness
        hp_freq = 5000 + self.features.get('brightness', 0.5) * 3000
        hp_freq = min(hp_freq, self.sr / 2 - 100)
        sos_hp = signal.butter(2, hp_freq, 'high', fs=self.sr, output='sos')
        hat = signal.sosfilt(sos_hp, hat)
        
        # Longer decay
        decay = 0.1 + self.features.get('entropy', 0.5) * 0.05
        env = np.exp(-t / decay)
        
        attack = np.minimum(t * 300, 1.0)
        
        hat = hat * env * attack
        hat = hat / np.max(np.abs(hat)) * 0.45
        
        return hat.astype(np.float32)
    
    # =========================================================================
    # CLAP - Clean layered clap
    # =========================================================================
    
    def synthesize_clap(self) -> np.ndarray:
        """Multi-layered clap with natural spread"""
        duration = 0.15
        samples = int(self.sr * duration)
        clap = np.zeros(samples)
        
        # Multiple noise bursts with slight delays
        num_layers = 4
        for i in range(num_layers):
            delay_samples = int(self.sr * 0.008 * i)  # 8ms between layers
            if delay_samples < samples:
                layer_len = samples - delay_samples
                t = np.linspace(0, duration - 0.008 * i, layer_len)
                
                # Band-passed noise
                noise = np.random.randn(layer_len)
                sos = signal.butter(3, [1000, 6000], 'band', fs=self.sr, output='sos')
                noise = signal.sosfilt(sos, noise)
                
                # Fast decay
                env = np.exp(-t / 0.05)
                
                clap[delay_samples:] += noise * env * (0.7 + 0.3 * i / num_layers)
        
        clap = np.tanh(clap * 1.5)
        clap = clap / np.max(np.abs(clap)) * 0.7
        
        return clap.astype(np.float32)
    
    # =========================================================================
    # PERCUSSION - Toms, shakers, etc
    # =========================================================================
    
    def synthesize_tom(self, pitch: float = 100) -> np.ndarray:
        """Simple tom/percussion hit"""
        duration = 0.25
        t = np.linspace(0, duration, int(self.sr * duration))
        
        # Pitch envelope drops
        pitch_env = pitch * (1 + 0.5 * np.exp(-t * 20))
        phase = np.cumsum(2 * np.pi * pitch_env / self.sr)
        tom = np.sin(phase)
        
        # Add body
        tom += 0.2 * np.sin(2 * phase) * np.exp(-t * 15)
        
        # Envelope
        env = np.exp(-t / 0.12)
        tom = tom * env
        tom = tom / np.max(np.abs(tom)) * 0.65
        
        return tom.astype(np.float32)
    
    # =========================================================================
    # MAIN RENDER FUNCTION
    # =========================================================================
    
    def render_midi_to_drums(self, midi_path: str, output_path: str, 
                             genre: str = 'HOUSE', 
                             image_features: Optional[Dict] = None) -> bool:
        """
        Render MIDI drum track using synthesized drums.
        
        Args:
            midi_path: Path to MIDI file
            output_path: Output WAV path
            genre: Genre name (HOUSE, EDM_CHILL, EDM_DROP, CINEMATIC)
            image_features: Optional 7D image features for variation
        """
        import mido
        
        # Set features if provided
        if image_features:
            self.set_image_features(image_features)
        
        # Normalize genre name
        genre_lower = genre.lower().replace('_', '')
        
        # Load MIDI
        midi = mido.MidiFile(midi_path)
        ticks_per_beat = midi.ticks_per_beat
        tempo = 500000  # Default: 120 BPM
        
        for track in midi.tracks:
            for msg in track:
                if msg.type == 'set_tempo':
                    tempo = msg.tempo
                    break
        
        seconds_per_tick = tempo / 1000000.0 / ticks_per_beat
        
        # Calculate duration
        max_tick = 0
        for track in midi.tracks:
            current_tick = 0
            for msg in track:
                current_tick += msg.time
            max_tick = max(max_tick, current_tick)
        
        duration = max_tick * seconds_per_tick + 2.0
        print(f"  MIDI duration: {duration:.2f}s, genre: {genre}")
        
        output = np.zeros(int(self.sr * duration), dtype=np.float32)
        
        # Pre-generate drum sounds for this genre
        if genre_lower in ['house']:
            kick = self.synthesize_kick_house()
            snare = self.synthesize_snare_house()
            hat_closed = self.synthesize_hihat_closed('house')
            hat_open = self.synthesize_hihat_open('house')
        elif genre_lower in ['edmchill', 'chill']:
            kick = self.synthesize_kick_chill()
            snare = self.synthesize_snare_chill()
            hat_closed = self.synthesize_hihat_closed('chill')
            hat_open = self.synthesize_hihat_open('chill')
        elif genre_lower in ['edmdrop', 'drop', 'edm']:
            kick = self.synthesize_kick_drop()
            snare = self.synthesize_snare_drop()
            hat_closed = self.synthesize_hihat_closed('edmdrop')
            hat_open = self.synthesize_hihat_open('edmdrop')
        elif genre_lower in ['cinematic', 'film', 'orchestral']:
            kick = self.synthesize_kick_cinematic()
            snare = self.synthesize_snare_cinematic()
            hat_closed = self.synthesize_hihat_closed('cinematic')
            hat_open = self.synthesize_hihat_open('cinematic')
        else:
            # Default to house
            kick = self.synthesize_kick_house()
            snare = self.synthesize_snare_house()
            hat_closed = self.synthesize_hihat_closed('house')
            hat_open = self.synthesize_hihat_open('house')
        
        clap = self.synthesize_clap()
        toms = {
            41: self.synthesize_tom(80),   # Low tom
            43: self.synthesize_tom(100),  # Floor tom
            45: self.synthesize_tom(130),  # Low-mid tom
            47: self.synthesize_tom(160),  # Mid tom
            48: self.synthesize_tom(200),  # High tom
            50: self.synthesize_tom(250),  # High tom 2
        }
        
        # Process MIDI
        note_count = 0
        
        for track in midi.tracks:
            current_tick = 0
            for msg in track:
                current_tick += msg.time
                
                if msg.type == 'note_on' and msg.velocity > 0:
                    time_sec = current_tick * seconds_per_tick
                    velocity = msg.velocity / 127.0
                    note = msg.note
                    
                    # Map MIDI notes to sounds
                    if note in [35, 36]:  # Kick
                        sound = kick.copy()
                    elif note in [38, 40]:  # Snare
                        sound = snare.copy()
                    elif note == 39:  # Clap
                        sound = clap.copy()
                    elif note in [42, 44]:  # Closed hi-hat
                        sound = hat_closed.copy()
                    elif note in [46, 49]:  # Open hi-hat
                        sound = hat_open.copy()
                    elif note in toms:  # Toms
                        sound = toms[note].copy()
                    else:
                        continue
                    
                    # Apply velocity
                    sound = sound * (0.5 + 0.5 * velocity)
                    
                    # Add subtle timing humanization (±5ms)
                    time_offset = random.gauss(0, 0.002)
                    time_sec = max(0, time_sec + time_offset)
                    
                    # Place in output
                    start = int(time_sec * self.sr)
                    end = min(start + len(sound), len(output))
                    if start < len(output) and start >= 0:
                        output[start:end] += sound[:end - start]
                        note_count += 1
        
        # Normalize with soft limiting
        if np.max(np.abs(output)) > 0:
            output = np.tanh(output * 0.7) * 0.95
        
        # Save
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        sf.write(output_path, output, self.sr)
        
        print(f"  Synthesized {note_count} drum hits for {genre}")
        return True


if __name__ == '__main__':
    print("Testing drum synthesis...")
    synth = DrumSynthesizer()
    
    # Test each genre's sounds
    for genre in ['house', 'chill', 'drop', 'cinematic']:
        print(f"\nTesting {genre} drums:")
        
        if genre == 'house':
            kick = synth.synthesize_kick_house()
            snare = synth.synthesize_snare_house()
        elif genre == 'chill':
            kick = synth.synthesize_kick_chill()
            snare = synth.synthesize_snare_chill()
        elif genre == 'drop':
            kick = synth.synthesize_kick_drop()
            snare = synth.synthesize_snare_drop()
        else:
            kick = synth.synthesize_kick_cinematic()
            snare = synth.synthesize_snare_cinematic()
        
        hat = synth.synthesize_hihat_closed(genre)
        
        sf.write(f'test_{genre}_kick.wav', kick, synth.sr)
        sf.write(f'test_{genre}_snare.wav', snare, synth.sr)
        sf.write(f'test_{genre}_hat.wav', hat, synth.sr)
        print(f"  ✓ {genre} drums saved")
    
    print("\nDrum synthesis test complete!")
