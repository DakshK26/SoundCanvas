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
        Classic 808 kick drum with pitch envelope - Enhanced for better sub bass
        
        Args:
            pitch: Starting pitch in Hz (typically 50-80)
            decay: Decay time in seconds
            punch: Transient punch amount (0-1)
        """
        duration = max(decay * 2.5, 1.0)  # Longer tail for sub
        t = np.linspace(0, duration, int(self.sr * duration))
        
        # Pitch envelope: starts high, drops quickly to fundamental (trap style)
        # More dramatic pitch drop for that "808 slide"
        pitch_env = pitch * (1 + 12 * np.exp(-t * 35))
        
        # Generate sine wave with pitch envelope (sub bass)
        phase = np.cumsum(2 * np.pi * pitch_env / self.sr)
        kick = np.sin(phase)
        
        # Add harmonic saturation for presence in smaller speakers
        kick += 0.3 * np.tanh(np.sin(2 * phase) * 2)
        
        # Amplitude envelope with fast attack and exponential decay
        amp_env = np.exp(-t / decay)
        
        # Add click/punch transient with high-frequency content
        click_env = np.exp(-t * 200)
        click = click_env * (np.random.randn(len(t)) * 0.15 + np.sin(2 * np.pi * 4000 * t) * 0.3)
        click = click * punch
        
        # Combine and apply soft clipping for warmth
        kick = kick * amp_env + click
        kick = np.tanh(kick * 1.2)  # Soft saturation
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
        Snare drum with tonal body and noise - Enhanced with layered transient
        """
        duration = 0.35  # Longer for more body
        t = np.linspace(0, duration, int(self.sr * duration))
        
        # Tonal component (shell resonance) - two body frequencies
        tone_body = np.sin(2 * np.pi * tone * t)
        tone_body += 0.5 * np.sin(2 * np.pi * tone * 1.5 * t)  # Inharmonic partial
        tone_body += 0.25 * np.sin(2 * np.pi * tone * 0.5 * t)  # Sub body
        
        # Pitch envelope for impact
        pitch_env = 1 + 2 * np.exp(-t * 80)
        tone_pitched = np.sin(2 * np.pi * tone * t * pitch_env)
        
        tone_body = 0.7 * tone_body + 0.3 * tone_pitched
        tone_env = np.exp(-t / (decay * 0.8))
        tonal = tone_body * tone_env
        
        # Noise component (snares) - layered high and mid
        noise = np.random.randn(len(t))
        
        # High-pass filter for snare rattle (crispy top)
        sos_hi = signal.butter(4, 3000, 'high', fs=self.sr, output='sos')
        noise_hi = signal.sosfilt(sos_hi, noise)
        
        # Band-pass for snare body (mid presence)
        sos_mid = signal.butter(3, [500, 3000], 'band', fs=self.sr, output='sos')
        noise_mid = signal.sosfilt(sos_mid, noise)
        
        noise_combined = 0.6 * noise_hi + 0.4 * noise_mid
        noise_env = np.exp(-t / decay)
        noise_out = noise_combined * noise_env
        
        # Transient crack
        transient = np.exp(-t * 300) * np.random.randn(len(t)) * 0.4
        
        # Mix tonal and noise
        snare = (1 - noise_mix) * tonal + noise_mix * noise_out + transient
        snare = np.tanh(snare * 2.5)  # Soft clipping for punch
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
        Metallic hihat using band-passed noise with resonant peaks - Enhanced realism
        """
        if closed:
            duration = 0.1
            decay = min(decay, 0.08)
        else:
            duration = 0.4
            decay = max(decay, 0.2)
        
        t = np.linspace(0, duration, int(self.sr * duration))
        
        # Start with noise
        hat = np.random.randn(len(t))
        
        # Multiple resonant peaks for metallic sound (cymbal frequencies)
        # Real hihats have inharmonic partials at specific ratios
        freqs = [tone * r for r in [1.0, 1.47, 1.89, 2.55, 3.24]]
        filtered = np.zeros_like(hat)
        
        for i, freq in enumerate(freqs):
            if freq < self.sr / 2:  # Nyquist check
                # Narrower Q for more defined ring
                low = max(freq * 0.95, 100)
                high = min(freq * 1.05, self.sr/2 - 100)
                if high > low:
                    sos = signal.butter(2, [low, high], 'band', fs=self.sr, output='sos')
                    filtered += signal.sosfilt(sos, hat) * (0.8 ** i)  # Higher partials quieter
        
        # Add high-frequency shimmer
        sos_hi = signal.butter(2, 10000, 'high', fs=self.sr, output='sos')
        shimmer = signal.sosfilt(sos_hi, hat) * 0.3
        filtered += shimmer
        
        # Envelope with sharper attack
        attack = np.minimum(t * 500, 1.0)  # 2ms attack
        release = np.exp(-t / decay)
        env = attack * release
        
        hat = filtered * env
        hat = np.tanh(hat * 4)  # Slight saturation
        hat = hat / np.max(np.abs(hat)) * 0.55
        
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
        
        # Genre-specific drum sounds with better variation
        genre_lower = genre.lower().replace('_', '')
        
        if genre_lower in ['rap', 'trap', 'hiphop']:
            # Trap/Rap: Deep 808, punchy snare, fast hats
            kick_gen = lambda v: self.synthesize_808_kick(
                pitch=45 + v * 0.15,  # Velocity affects pitch slightly
                decay=0.7 + v * 0.003,
                punch=0.9
            )
            snare_gen = lambda v: self.synthesize_snare(
                tone=170 + v * 0.3,
                decay=0.2,
                noise_mix=0.55
            )
            hat_closed_gen = lambda v: self.synthesize_hihat(closed=True, tone=9000, decay=0.05)
            hat_open_gen = lambda v: self.synthesize_hihat(closed=False, tone=8500, decay=0.25)
            
        elif genre_lower in ['rnb', 'rb']:
            # R&B: Soft rounded kick, warm snare, gentle hats
            kick_gen = lambda v: self.synthesize_house_kick(
                pitch=55,
                decay=0.3
            )
            snare_gen = lambda v: self.synthesize_snare(
                tone=180,
                decay=0.18,
                noise_mix=0.4  # Less noise = warmer
            )
            hat_closed_gen = lambda v: self.synthesize_hihat(closed=True, tone=7000, decay=0.06)
            hat_open_gen = lambda v: self.synthesize_hihat(closed=False, tone=6500, decay=0.18)
            
        elif genre_lower in ['house']:
            # House: Tight 4-on-floor kick, snappy snare
            kick_gen = lambda v: self.synthesize_house_kick(
                pitch=65,
                decay=0.3
            )
            snare_gen = lambda v: self.synthesize_snare(
                tone=230,
                decay=0.12,
                noise_mix=0.75  # More noise = tighter
            )
            hat_closed_gen = lambda v: self.synthesize_hihat(closed=True, tone=10000, decay=0.04)
            hat_open_gen = lambda v: self.synthesize_hihat(closed=False, tone=9000, decay=0.15)
            
        elif genre_lower in ['edmdrop', 'edm']:
            # EDM Drop: Big punchy kick, aggressive snare
            kick_gen = lambda v: self.synthesize_house_kick(
                pitch=60,
                decay=0.35
            )
            snare_gen = lambda v: self.synthesize_snare(
                tone=210,
                decay=0.15,
                noise_mix=0.7
            )
            hat_closed_gen = lambda v: self.synthesize_hihat(closed=True, tone=9500, decay=0.05)
            hat_open_gen = lambda v: self.synthesize_hihat(closed=False, tone=8500, decay=0.2)
            
        elif genre_lower in ['edmchill', 'chill']:
            # EDM Chill: Soft kick, muted snare, subtle hats
            kick_gen = lambda v: self.synthesize_808_kick(
                pitch=50,
                decay=0.4,
                punch=0.5
            )
            snare_gen = lambda v: self.synthesize_snare(
                tone=190,
                decay=0.2,
                noise_mix=0.45
            )
            hat_closed_gen = lambda v: self.synthesize_hihat(closed=True, tone=7500, decay=0.07)
            hat_open_gen = lambda v: self.synthesize_hihat(closed=False, tone=7000, decay=0.2)
            
        elif genre_lower in ['cinematic', 'film', 'orchestral']:
            # Cinematic: Soft timpani-like kick, orchestral snare, subtle percussion
            kick_gen = lambda v: self.synthesize_808_kick(
                pitch=40,  # Lower pitch for orchestral feel
                decay=0.6,
                punch=0.4  # Less punch, more body
            )
            snare_gen = lambda v: self.synthesize_snare(
                tone=220,
                decay=0.25,
                noise_mix=0.5
            )
            hat_closed_gen = lambda v: self.synthesize_hihat(closed=True, tone=6000, decay=0.08)
            hat_open_gen = lambda v: self.synthesize_hihat(closed=False, tone=5500, decay=0.25)
            
        elif genre_lower in ['retrowave', 'synthwave', '80s']:
            # Retrowave: Punchy gated snare, electronic kick, shimmering hats
            kick_gen = lambda v: self.synthesize_house_kick(
                pitch=58,
                decay=0.25
            )
            snare_gen = lambda v: self.synthesize_snare(
                tone=250,  # Higher pitch for 80s gated sound
                decay=0.1,  # Short for gated effect
                noise_mix=0.8
            )
            hat_closed_gen = lambda v: self.synthesize_hihat(closed=True, tone=11000, decay=0.04)
            hat_open_gen = lambda v: self.synthesize_hihat(closed=False, tone=10000, decay=0.22)
            
        else:
            # Default balanced EDM sound
            kick_gen = lambda v: self.synthesize_808_kick(pitch=55, decay=0.5, punch=0.65)
            snare_gen = lambda v: self.synthesize_snare(tone=200, decay=0.15, noise_mix=0.6)
            hat_closed_gen = lambda v: self.synthesize_hihat(closed=True, tone=8500, decay=0.06)
            hat_open_gen = lambda v: self.synthesize_hihat(closed=False, tone=8000, decay=0.18)
        
        # Process MIDI events - convert ticks to seconds properly
        # Get ticks per beat and calculate tempo
        ticks_per_beat = midi.ticks_per_beat
        tempo = 500000  # Default: 120 BPM (500000 microseconds per beat)
        
        # Find tempo from MIDI meta messages
        for track in midi.tracks:
            for msg in track:
                if msg.type == 'set_tempo':
                    tempo = msg.tempo
                    break
        
        # Calculate seconds per tick
        seconds_per_tick = tempo / 1000000.0 / ticks_per_beat
        print(f"  MIDI timing: {ticks_per_beat} ticks/beat, tempo={tempo}, sec/tick={seconds_per_tick:.6f}")
        
        note_count = 0
        
        for track in midi.tracks:
            current_tick = 0
            for msg in track:
                current_tick += msg.time
                current_time_sec = current_tick * seconds_per_tick
                
                if msg.type == 'note_on' and msg.velocity > 0:
                    note = msg.note
                    velocity = msg.velocity / 127.0
                    
                    # Map MIDI notes to drum sounds
                    if note in [35, 36]:  # Kick
                        drum_sound = kick_gen(velocity)
                    elif note in [38, 40]:  # Snare
                        drum_sound = snare_gen(velocity)
                    elif note == 39:  # Clap
                        drum_sound = self.synthesize_clap()
                    elif note in [42, 44]:  # Closed hihat
                        drum_sound = hat_closed_gen(velocity)
                    elif note in [46, 49]:  # Open hihat
                        drum_sound = hat_open_gen(velocity)
                    elif note in [41, 43, 45, 47, 48, 50]:  # Toms/percussion
                        pitch = 150 + (note - 41) * 40
                        drum_sound = self.synthesize_percussion(pitch=pitch, decay=0.15)
                    else:
                        continue
                    
                    # Apply velocity
                    drum_sound = drum_sound * (0.5 + 0.5 * velocity)  # Min 50% volume
                    
                    # Add to output at correct time position
                    start_sample = int(current_time_sec * self.sr)
                    end_sample = min(start_sample + len(drum_sound), len(output))
                    if start_sample < len(output):
                        output[start_sample:end_sample] += drum_sound[:end_sample - start_sample]
                        note_count += 1
        
        # Normalize and save
        if np.max(np.abs(output)) > 0:
            # Soft limiting instead of hard normalization
            output = np.tanh(output * 0.8) * 0.95
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        sf.write(output_path, output, self.sr)
        
        print(f"  Synthesized {note_count} drum hits for genre '{genre}'")
        
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
