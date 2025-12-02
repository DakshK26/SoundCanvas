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
        
        # Fade-out to prevent clicks on rapid repeats (4-on-floor)
        fadeout_samples = min(int(0.005 * self.sr), len(kick) // 4)
        kick[-fadeout_samples:] *= np.linspace(1, 0, fadeout_samples)
        
        if np.max(np.abs(kick)) > 0:
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
        
        # Fade-out to prevent end clicks
        fadeout_samples = min(int(0.008 * self.sr), len(kick) // 4)
        kick[-fadeout_samples:] *= np.linspace(1, 0, fadeout_samples)
        
        if np.max(np.abs(kick)) > 0:
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
        
        # Short fade-out (drop kicks are tight)
        fadeout_samples = min(int(0.003 * self.sr), len(kick) // 4)
        kick[-fadeout_samples:] *= np.linspace(1, 0, fadeout_samples)
        
        if np.max(np.abs(kick)) > 0:
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
        
        # Longer fade-out for cinematic tail
        fadeout_samples = min(int(0.015 * self.sr), len(kick) // 4)
        kick[-fadeout_samples:] *= np.linspace(1, 0, fadeout_samples)
        
        if np.max(np.abs(kick)) > 0:
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
        
        # Smooth attack ramp to prevent clicks
        attack_samples = int(0.001 * self.sr)  # 1ms attack
        attack = np.ones(len(t))
        attack[:attack_samples] = np.linspace(0, 1, attack_samples)
        
        # Tonal body (tuned membrane)
        tone_freq = 180 + self.features.get('saturation', 0.5) * 40
        tone = np.sin(2 * np.pi * tone_freq * t)
        tone += 0.3 * np.sin(2 * np.pi * tone_freq * 1.5 * t)  # Overtone
        tone_env = np.exp(-t / 0.08)
        tonal = tone * tone_env * attack
        
        # Noise body (snare wires) - apply envelope BEFORE filtering
        noise = np.random.randn(len(t))
        noise_env = np.exp(-t / 0.1)
        noise = noise * noise_env * attack  # Apply envelope first
        
        # Band-pass 1000-8000 Hz for snare character
        sos = signal.butter(2, [1000, 8000], 'band', fs=self.sr, output='sos')
        noise_out = signal.sosfilt(sos, noise)
        
        # Click transient (already has fast decay, no click issues)
        click = np.exp(-t * 200) * 0.3 * attack
        
        # Mix: House snares are fairly balanced
        snare = 0.4 * tonal + 0.5 * noise_out + click
        
        # Apply fade-out to prevent end clicks
        fadeout_samples = min(int(0.005 * self.sr), len(snare) // 4)
        snare[-fadeout_samples:] *= np.linspace(1, 0, fadeout_samples)
        
        snare = np.tanh(snare * 2)
        if np.max(np.abs(snare)) > 0:
            snare = snare / np.max(np.abs(snare)) * 0.8
        
        return snare.astype(np.float32)
    
    def synthesize_snare_chill(self) -> np.ndarray:
        """
        Chill snare: Softer, warmer, less aggressive.
        More tone, less bright noise. Lo-fi/downtempo character.
        """
        duration = 0.25
        t = np.linspace(0, duration, int(self.sr * duration))
        
        # Smooth attack ramp to prevent clicks
        attack_samples = int(0.002 * self.sr)  # 2ms attack (softer than house)
        attack = np.ones(len(t))
        attack[:attack_samples] = np.linspace(0, 1, attack_samples)
        
        # Lower, warmer tone - chill uses lower fundamental for warmth
        tone_freq = 150 + self.features.get('brightness', 0.5) * 30  # 150-180Hz
        tone = np.sin(2 * np.pi * tone_freq * t)
        tone += 0.4 * np.sin(2 * np.pi * tone_freq * 1.4 * t)  # Slightly detuned harmonic
        tone_env = np.exp(-t / 0.12)  # Longer decay than house
        tonal = tone * tone_env * attack
        
        # Softer noise - apply envelope BEFORE filtering
        noise = np.random.randn(len(t))
        noise_env = np.exp(-t / 0.15)
        noise = noise * noise_env * attack  # Apply envelope first
        
        # Lower frequency band for warmer character (differs from house's 1k-8k)
        sos = signal.butter(2, [800, 5000], 'band', fs=self.sr, output='sos')
        noise_out = signal.sosfilt(sos, noise)
        
        # Soft click (gentler than house)
        click = np.exp(-t * 100) * 0.15 * attack
        
        # More tonal, less noise (opposite ratio from house - warmer sound)
        snare = 0.5 * tonal + 0.3 * noise_out + click
        
        # Fade-out to prevent end clicks
        fadeout_samples = min(int(0.008 * self.sr), len(snare) // 4)
        snare[-fadeout_samples:] *= np.linspace(1, 0, fadeout_samples)
        
        snare = np.tanh(snare * 1.5)  # Less saturation than house
        if np.max(np.abs(snare)) > 0:
            snare = snare / np.max(np.abs(snare)) * 0.7
        
        return snare.astype(np.float32)
    
    def synthesize_snare_drop(self) -> np.ndarray:
        """
        EDM Drop snare: Aggressive, bright, cutting.
        Heavy noise, strong transient. Festival-ready impact.
        """
        duration = 0.18
        t = np.linspace(0, duration, int(self.sr * duration))
        
        # Very short attack for aggressive transient (EDM needs punch)
        attack_samples = int(0.0005 * self.sr)  # 0.5ms attack - very fast
        attack = np.ones(len(t))
        attack[:attack_samples] = np.linspace(0, 1, attack_samples)
        
        # Higher, aggressive tone - drop snares cut through the mix
        tone_freq = 200 + self.features.get('sharpness', 0.5) * 50  # 200-250Hz
        tone = np.sin(2 * np.pi * tone_freq * t)
        tone += 0.2 * np.sin(2 * np.pi * tone_freq * 2 * t)  # Octave harmonic
        tone_env = np.exp(-t / 0.06)  # Fast decay
        tonal = tone * tone_env * attack
        
        # Bright, aggressive noise - apply envelope BEFORE filtering
        noise = np.random.randn(len(t))
        noise_env = np.exp(-t / 0.08)
        noise = noise * noise_env * attack  # Apply envelope first
        
        # Higher frequency band for brightness (brighter than house/chill)
        # Cap at safe Nyquist distance
        high_freq = min(12000, self.sr * 0.45)
        sos = signal.butter(2, [2000, high_freq], 'band', fs=self.sr, output='sos')
        noise_out = signal.sosfilt(sos, noise)
        
        # Strong transient click
        click = np.exp(-t * 300) * 0.5 * attack
        
        # More noise than tone (opposite of chill - aggressive character)
        snare = 0.3 * tonal + 0.6 * noise_out + click
        
        # Short fade-out
        fadeout_samples = min(int(0.003 * self.sr), len(snare) // 4)
        snare[-fadeout_samples:] *= np.linspace(1, 0, fadeout_samples)
        
        snare = np.tanh(snare * 2.5)  # Heavy saturation for aggression
        if np.max(np.abs(snare)) > 0:
            snare = snare / np.max(np.abs(snare)) * 0.9
        
        return snare.astype(np.float32)
    
    def synthesize_snare_cinematic(self) -> np.ndarray:
        """
        Cinematic snare: Dramatic, roomy, orchestral feel.
        More tone and reverb-like tail. Think Hans Zimmer.
        """
        duration = 0.35
        t = np.linspace(0, duration, int(self.sr * duration))
        
        # Gentle attack for orchestral feel (not punchy like EDM)
        attack_samples = int(0.003 * self.sr)  # 3ms attack
        attack = np.ones(len(t))
        attack[:attack_samples] = np.linspace(0, 1, attack_samples)
        
        # Deep, dramatic tone - lower than other genres for gravitas
        tone_freq = 160 + self.features.get('contrast', 0.5) * 30  # 160-190Hz
        tone = np.sin(2 * np.pi * tone_freq * t)
        tone += 0.5 * np.sin(2 * np.pi * tone_freq * 1.3 * t)  # Fifth harmonic for richness
        tone_env = np.exp(-t / 0.15)  # Long decay for drama
        tonal = tone * tone_env * attack
        
        # Warmer noise (like concert hall snare) - apply envelope BEFORE filtering
        noise = np.random.randn(len(t))
        noise_env = np.exp(-t / 0.2)  # Longest noise decay of all genres
        noise = noise * noise_env * attack  # Apply envelope first
        
        # Lower, warmer frequency band (orchestral warmth)
        sos = signal.butter(2, [600, 6000], 'band', fs=self.sr, output='sos')
        noise_out = signal.sosfilt(sos, noise)
        
        # Subtle, soft click (not aggressive)
        click = np.exp(-t * 80) * 0.2 * attack
        
        # Balanced mix with long tail (more reverberant character)
        snare = 0.5 * tonal + 0.4 * noise_out + click
        
        # Longer fade-out for cinematic tail
        fadeout_samples = min(int(0.015 * self.sr), len(snare) // 4)
        snare[-fadeout_samples:] *= np.linspace(1, 0, fadeout_samples)
        
        snare = np.tanh(snare * 1.3)  # Gentle saturation
        if np.max(np.abs(snare)) > 0:
            snare = snare / np.max(np.abs(snare)) * 0.75
        
        return snare.astype(np.float32)
    
    # =========================================================================
    # HI-HATS - Clean, genre-appropriate character
    # =========================================================================
    
    def synthesize_hihat_closed(self, genre: str = 'house') -> np.ndarray:
        """
        Closed hi-hat: Short, tight, clean.
        Genre-specific character without metallic harshness.
        
        - House: Crisp, punchy, offbeat-ready
        - Chill: Softer, warmer, lo-fi character
        - EDM Drop: Bright, cutting, aggressive
        - Cinematic: Subtle, refined, orchestral
        """
        # Genre-specific durations
        if genre in ['house']:
            duration = 0.05  # Tight for offbeat patterns
        elif genre in ['edmdrop']:
            duration = 0.04  # Very tight and punchy
        elif genre in ['chill']:
            duration = 0.08  # Slightly longer, relaxed
        else:  # cinematic
            duration = 0.06
            
        t = np.linspace(0, duration, int(self.sr * duration))
        
        # Pure noise base
        hat = np.random.randn(len(t))
        
        # Genre-specific decay (controlled by sharpness for variation)
        base_sharpness = self.features.get('sharpness', 0.5)
        if genre in ['house']:
            decay = 0.015 + (1 - base_sharpness) * 0.015  # 15-30ms
        elif genre in ['edmdrop']:
            decay = 0.010 + (1 - base_sharpness) * 0.010  # 10-20ms (tightest)
        elif genre in ['chill']:
            decay = 0.025 + (1 - base_sharpness) * 0.020  # 25-45ms (most relaxed)
        else:  # cinematic
            decay = 0.020 + (1 - base_sharpness) * 0.015  # 20-35ms
        
        env = np.exp(-t / decay)
        
        # Smooth attack ramp (prevents clicks)
        attack_samples = int(0.001 * self.sr)  # 1ms attack
        attack = np.ones(len(t))
        if attack_samples < len(t):
            attack[:attack_samples] = np.linspace(0, 1, attack_samples)
        
        # Apply envelope to noise BEFORE filtering
        hat = hat * env * attack
        
        # Genre-specific frequency bands (brightness modulates within range)
        brightness = self.features.get('brightness', 0.5)
        
        if genre in ['house']:
            # House: Clean, present but not harsh (6k-12k range)
            low_freq = 5500 + brightness * 1500   # 5.5k-7k
            high_freq = 11000 + brightness * 2000  # 11k-13k
        elif genre in ['edmdrop']:
            # EDM Drop: Brightest, most cutting (7k-14k range)  
            low_freq = 6000 + brightness * 2000   # 6k-8k
            high_freq = 12000 + brightness * 2000  # 12k-14k
        elif genre in ['chill']:
            # Chill: Warmest, lo-fi character (4k-9k range)
            low_freq = 4000 + brightness * 1000   # 4k-5k
            high_freq = 8000 + brightness * 2000   # 8k-10k
        else:  # cinematic
            # Cinematic: Refined, not too bright (5k-10k range)
            low_freq = 4500 + brightness * 1500   # 4.5k-6k
            high_freq = 9000 + brightness * 2000   # 9k-11k
        
        # Cap at safe Nyquist distance
        high_freq = min(high_freq, self.sr * 0.45)
        low_freq = min(low_freq, high_freq - 1000)  # Ensure valid range
        
        sos_bp = signal.butter(2, [low_freq, high_freq], 'band', fs=self.sr, output='sos')
        hat = signal.sosfilt(sos_bp, hat)
        
        # Fade-out to prevent end clicks
        fadeout_samples = min(int(0.003 * self.sr), len(hat) // 4)
        hat[-fadeout_samples:] *= np.linspace(1, 0, fadeout_samples)
        
        # Genre-specific output levels
        if genre in ['edmdrop']:
            level = 0.55  # Slightly louder for aggression
        elif genre in ['chill']:
            level = 0.40  # Quieter, sits back in mix
        else:
            level = 0.50
            
        if np.max(np.abs(hat)) > 0:
            hat = hat / np.max(np.abs(hat)) * level
        
        return hat.astype(np.float32)
    
    def synthesize_hihat_open(self, genre: str = 'house') -> np.ndarray:
        """
        Open hi-hat: Longer, ringing, clean.
        Genre-specific sustain and brightness.
        """
        # Genre-specific durations
        if genre in ['house']:
            duration = 0.18  # Standard open hat
        elif genre in ['edmdrop']:
            duration = 0.15  # Shorter, tighter
        elif genre in ['chill']:
            duration = 0.28  # Longest, most relaxed
        else:  # cinematic
            duration = 0.22  # Moderate with tail
            
        t = np.linspace(0, duration, int(self.sr * duration))
        
        # Noise base
        hat = np.random.randn(len(t))
        
        # Genre-specific decay (entropy affects sustain)
        entropy = self.features.get('entropy', 0.5)
        if genre in ['house']:
            decay = 0.08 + entropy * 0.04  # 80-120ms
        elif genre in ['edmdrop']:
            decay = 0.06 + entropy * 0.03  # 60-90ms (tighter)
        elif genre in ['chill']:
            decay = 0.12 + entropy * 0.06  # 120-180ms (longest)
        else:  # cinematic
            decay = 0.10 + entropy * 0.05  # 100-150ms
        
        env = np.exp(-t / decay)
        
        # Smooth attack ramp
        attack_samples = int(0.002 * self.sr)  # 2ms attack
        attack = np.ones(len(t))
        if attack_samples < len(t):
            attack[:attack_samples] = np.linspace(0, 1, attack_samples)
        
        # Apply envelope BEFORE filtering
        hat = hat * env * attack
        
        # Genre-specific frequency bands (slightly lower than closed for fullness)
        brightness = self.features.get('brightness', 0.5)
        
        if genre in ['house']:
            low_freq = 4500 + brightness * 1500
            high_freq = 10000 + brightness * 2000
        elif genre in ['edmdrop']:
            low_freq = 5000 + brightness * 2000
            high_freq = 11000 + brightness * 2000
        elif genre in ['chill']:
            low_freq = 3500 + brightness * 1000
            high_freq = 7500 + brightness * 2000
        else:  # cinematic
            low_freq = 4000 + brightness * 1500
            high_freq = 8500 + brightness * 2000
        
        high_freq = min(high_freq, self.sr * 0.45)
        low_freq = min(low_freq, high_freq - 1000)
        
        sos_bp = signal.butter(2, [low_freq, high_freq], 'band', fs=self.sr, output='sos')
        hat = signal.sosfilt(sos_bp, hat)
        
        # Longer fade-out for open hats
        fadeout_samples = min(int(0.008 * self.sr), len(hat) // 4)
        hat[-fadeout_samples:] *= np.linspace(1, 0, fadeout_samples)
        
        # Genre-specific output levels
        if genre in ['edmdrop']:
            level = 0.50
        elif genre in ['chill']:
            level = 0.38
        else:
            level = 0.45
            
        if np.max(np.abs(hat)) > 0:
            hat = hat / np.max(np.abs(hat)) * level
        
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
                
                # Apply envelope BEFORE filtering
                env = np.exp(-t / 0.05)
                
                # Smooth attack for this layer
                attack_samples = int(0.001 * self.sr)  # 1ms attack
                attack = np.ones(layer_len)
                if attack_samples < layer_len:
                    attack[:attack_samples] = np.linspace(0, 1, attack_samples)
                
                noise = noise * env * attack
                
                sos = signal.butter(3, [1000, 6000], 'band', fs=self.sr, output='sos')
                noise = signal.sosfilt(sos, noise)
                
                clap[delay_samples:] += noise * (0.7 + 0.3 * i / num_layers)
        
        # Apply fade-out to prevent end clicks
        fadeout_samples = min(int(0.005 * self.sr), samples // 4)
        clap[-fadeout_samples:] *= np.linspace(1, 0, fadeout_samples)
        
        clap = np.tanh(clap * 1.5)
        if np.max(np.abs(clap)) > 0:
            clap = clap / np.max(np.abs(clap)) * 0.7
        
        return clap.astype(np.float32)
    
    # =========================================================================
    # PERCUSSION - Toms, shakers, etc
    # =========================================================================
    
    def synthesize_tom(self, pitch: float = 100) -> np.ndarray:
        """Simple tom/percussion hit with proper attack/decay"""
        duration = 0.25
        t = np.linspace(0, duration, int(self.sr * duration))
        
        # Smooth attack ramp to prevent clicks
        attack_samples = int(0.002 * self.sr)  # 2ms attack
        attack = np.ones(len(t))
        attack[:attack_samples] = np.linspace(0, 1, attack_samples)
        
        # Pitch envelope drops (characteristic tom sound)
        pitch_env = pitch * (1 + 0.5 * np.exp(-t * 20))
        phase = np.cumsum(2 * np.pi * pitch_env / self.sr)
        tom = np.sin(phase)
        
        # Add body with second harmonic
        tom += 0.2 * np.sin(2 * phase) * np.exp(-t * 15)
        
        # Envelope with attack
        env = np.exp(-t / 0.12)
        tom = tom * env * attack
        
        # Fade-out to prevent end clicks
        fadeout_samples = min(int(0.008 * self.sr), len(tom) // 4)
        tom[-fadeout_samples:] *= np.linspace(1, 0, fadeout_samples)
        
        if np.max(np.abs(tom)) > 0:
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
