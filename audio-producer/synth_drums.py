"""
Synthesized Drum Generator
Creates high-quality drums using synthesis instead of samples
Supports genre-specific drum sounds (808s, house kicks, acoustic drums)
"""

import numpy as np
from scipy import signal
from typing import Dict, Tuple
import soundfile as sf
from pathlib import Path


class DrumSynthesizer:
    """
    Synthesizes drum sounds procedurally
    Much better quality than samples, with genre-specific tuning
    """
    
    def __init__(self, samplerate: int = 44100):
        self.sr = samplerate
        
    def synthesize_808_kick(self, pitch: float = 50, decay: float = 0.5, punch: float = 0.7) -> np.ndarray:
        """
        Classic 808 kick drum with pitch envelope
        
        Args:
            pitch: Starting pitch in Hz (typically 50-80)
            decay: Decay time in seconds
            punch: Transient punch amount (0-1)
        """
        duration = max(decay * 2, 0.8)
        t = np.linspace(0, duration, int(self.sr * duration))
        
        # Pitch envelope: starts high, drops quickly to fundamental
        pitch_env = pitch * (1 + 8 * np.exp(-t * 40))
        
        # Generate sine wave with pitch envelope
        phase = np.cumsum(2 * np.pi * pitch_env / self.sr)
        kick = np.sin(phase)
        
        # Amplitude envelope with fast attack and exponential decay
        amp_env = np.exp(-t / decay)
        
        # Add click/punch transient
        click = np.exp(-t * 150) * np.random.randn(len(t)) * punch * 0.3
        
        # Combine and normalize
        kick = kick * amp_env + click
        kick = kick / np.max(np.abs(kick)) * 0.95
        
        return kick.astype(np.float32)
    
    def synthesize_house_kick(self, pitch: float = 60, decay: float = 0.4) -> np.ndarray:
        """
        Tight house kick with harmonic saturation
        """
        duration = 0.6
        t = np.linspace(0, duration, int(self.sr * duration))
        
        # Pitch envelope - less dramatic than 808
        pitch_env = pitch * (1 + 3 * np.exp(-t * 30))
        
        # Generate fundamental + harmonics
        phase = np.cumsum(2 * np.pi * pitch_env / self.sr)
        kick = np.sin(phase)
        kick += 0.3 * np.sin(2 * phase)  # 2nd harmonic
        
        # Tight amplitude envelope
        amp_env = np.exp(-t / decay)
        
        # Sharp transient
        transient = np.exp(-t * 200) * 0.4
        
        kick = kick * amp_env + transient
        kick = np.tanh(kick * 1.5)  # Soft saturation
        kick = kick / np.max(np.abs(kick)) * 0.95
        
        return kick.astype(np.float32)
    
    def synthesize_snare(self, tone: float = 200, decay: float = 0.15, noise_mix: float = 0.6) -> np.ndarray:
        """
        Snare drum with tonal body and noise
        """
        duration = 0.25
        t = np.linspace(0, duration, int(self.sr * duration))
        
        # Tonal component (shell resonance)
        tone_body = np.sin(2 * np.pi * tone * t)
        tone_body += 0.5 * np.sin(2 * np.pi * tone * 1.5 * t)  # Inharmonic partial
        tone_env = np.exp(-t / (decay * 0.8))
        tonal = tone_body * tone_env
        
        # Noise component (snares)
        noise = np.random.randn(len(t))
        
        # High-pass filter for snare rattle
        sos = signal.butter(4, 2000, 'high', fs=self.sr, output='sos')
        noise = signal.sosfilt(sos, noise)
        
        noise_env = np.exp(-t / decay)
        noise = noise * noise_env
        
        # Mix tonal and noise
        snare = (1 - noise_mix) * tonal + noise_mix * noise
        snare = np.tanh(snare * 2)
        snare = snare / np.max(np.abs(snare)) * 0.85
        
        return snare.astype(np.float32)
    
    def synthesize_clap(self, layers: int = 3, spread: float = 0.02) -> np.ndarray:
        """
        Multi-layered clap with stereo spread
        """
        duration = 0.2
        base_samples = int(self.sr * duration)
        
        clap = np.zeros(base_samples)
        
        # Create multiple impulses with slight delay (clap layers)
        for i in range(layers):
            delay = int(self.sr * spread * i)
            if delay < base_samples:
                # Filtered noise burst
                noise = np.random.randn(base_samples - delay)
                
                # Band-pass filter
                sos = signal.butter(4, [800, 4000], 'band', fs=self.sr, output='sos')
                noise = signal.sosfilt(sos, noise)
                
                # Envelope
                t = np.linspace(0, duration - spread * i, len(noise))
                env = np.exp(-t / 0.08)
                
                # Add to clap with slight variation
                clap[delay:] += noise * env * (0.8 + 0.2 * i / layers)
        
        clap = np.tanh(clap * 2)
        clap = clap / np.max(np.abs(clap)) * 0.8
        
        return clap.astype(np.float32)
    
    def synthesize_hihat(self, closed: bool = True, tone: float = 8000, decay: float = 0.08) -> np.ndarray:
        """
        Metallic hihat using band-passed noise
        """
        if closed:
            duration = 0.08
            decay = min(decay, 0.1)
        else:
            duration = 0.3
            decay = max(decay, 0.15)
        
        t = np.linspace(0, duration, int(self.sr * duration))
        
        # Start with noise
        hat = np.random.randn(len(t))
        
        # Multiple resonant peaks for metallic sound
        freqs = [tone * r for r in [1.0, 1.42, 1.89, 2.45]]
        filtered = np.zeros_like(hat)
        
        for freq in freqs:
            sos = signal.butter(2, [freq * 0.9, freq * 1.1], 'band', fs=self.sr, output='sos')
            filtered += signal.sosfilt(sos, hat)
        
        # Envelope
        env = np.exp(-t / decay)
        
        hat = filtered * env
        hat = np.tanh(hat * 3)
        hat = hat / np.max(np.abs(hat)) * 0.6
        
        return hat.astype(np.float32)
    
    def synthesize_percussion(self, pitch: float = 300, decay: float = 0.12, metallic: float = 0.3) -> np.ndarray:
        """
        Generic percussion sound (toms, shakers, etc)
        """
        duration = 0.2
        t = np.linspace(0, duration, int(self.sr * duration))
        
        # Tonal component
        tonal = np.sin(2 * np.pi * pitch * t)
        tonal += 0.3 * np.sin(2 * np.pi * pitch * 1.6 * t)  # Inharmonic
        
        # Noise component
        noise = np.random.randn(len(t))
        sos = signal.butter(3, [pitch * 0.8, pitch * 4], 'band', fs=self.sr, output='sos')
        noise = signal.sosfilt(sos, noise)
        
        # Mix based on metallic parameter
        perc = (1 - metallic) * tonal + metallic * noise
        
        # Envelope
        env = np.exp(-t / decay)
        perc = perc * env
        
        perc = perc / np.max(np.abs(perc)) * 0.7
        
        return perc.astype(np.float32)
    
    def render_midi_to_drums(self, midi_path: str, output_path: str, genre: str = 'edm') -> bool:
        """
        Render MIDI drum track to audio using synthesis
        
        Args:
            midi_path: Path to MIDI file
            output_path: Output WAV path
            genre: Genre for drum sound selection
        """
        import mido
        
        # Load MIDI
        midi = mido.MidiFile(midi_path)
        
        # Calculate duration
        total_time = midi.length
        duration = total_time + 2  # Add 2s tail
        output = np.zeros(int(self.sr * duration), dtype=np.float32)
        
        # Genre-specific drum sounds
        if genre.lower() in ['rap', 'trap', 'hip-hop']:
            kick_gen = lambda: self.synthesize_808_kick(pitch=55, decay=0.6, punch=0.8)
            snare_gen = lambda: self.synthesize_snare(tone=180, decay=0.18, noise_mix=0.5)
        elif genre.lower() in ['edm', 'house', 'edm_drop', 'edm_chill']:
            kick_gen = lambda: self.synthesize_house_kick(pitch=65, decay=0.35)
            snare_gen = lambda: self.synthesize_snare(tone=220, decay=0.15, noise_mix=0.7)
        else:
            kick_gen = lambda: self.synthesize_808_kick(pitch=60, decay=0.5, punch=0.6)
            snare_gen = lambda: self.synthesize_snare(tone=200, decay=0.15, noise_mix=0.6)
        
        # Process MIDI events
        current_time = 0
        
        for track in midi.tracks:
            current_time = 0
            for msg in track:
                current_time += msg.time
                
                if msg.type == 'note_on' and msg.velocity > 0:
                    note = msg.note
                    velocity = msg.velocity / 127.0
                    
                    # Map MIDI notes to drum sounds
                    if note in [35, 36]:  # Kick
                        drum_sound = kick_gen()
                    elif note in [38, 40]:  # Snare
                        drum_sound = snare_gen()
                    elif note == 39:  # Clap
                        drum_sound = self.synthesize_clap()
                    elif note in [42, 44]:  # Closed hihat
                        drum_sound = self.synthesize_hihat(closed=True)
                    elif note in [46, 49]:  # Open hihat
                        drum_sound = self.synthesize_hihat(closed=False)
                    elif note in [41, 43, 45, 47, 48, 50]:  # Toms/percussion
                        pitch = 200 + (note - 41) * 30
                        drum_sound = self.synthesize_percussion(pitch=pitch, decay=0.15)
                    else:
                        continue
                    
                    # Apply velocity
                    drum_sound = drum_sound * velocity
                    
                    # Add to output
                    start_sample = int(current_time * self.sr)
                    end_sample = min(start_sample + len(drum_sound), len(output))
                    output[start_sample:end_sample] += drum_sound[:end_sample - start_sample]
        
        # Normalize and save
        if np.max(np.abs(output)) > 0:
            output = output / np.max(np.abs(output)) * 0.95
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        sf.write(output_path, output, self.sr)
        
        return True


if __name__ == '__main__':
    # Test synthesis
    synth = DrumSynthesizer()
    
    print("Testing drum synthesis...")
    
    # Test 808 kick
    kick = synth.synthesize_808_kick()
    sf.write('test_808_kick.wav', kick, synth.sr)
    print("✓ 808 kick")
    
    # Test snare
    snare = synth.synthesize_snare()
    sf.write('test_snare.wav', snare, synth.sr)
    print("✓ Snare")
    
    # Test hihat
    hihat = synth.synthesize_hihat(closed=True)
    sf.write('test_hihat.wav', hihat, synth.sr)
    print("✓ Hihat")
    
    print("\nDrum synthesis test complete!")
