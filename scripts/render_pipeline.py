#!/usr/bin/env python3
"""
Phase 8 - Person B: Audio Rendering Pipeline
Renders MIDI files to high-quality WAV with per-track effects and mixing
"""

import sys
import os
import subprocess
import tempfile
import numpy as np
from scipy.io import wavfile
from scipy import signal
import json

class AudioRenderPipeline:
    def __init__(self, soundfont_path="/usr/share/sounds/sf2/FluidR3_GM.sf2"):
        self.soundfont = soundfont_path
        self.sample_rate = 44100
        
    def render_midi_to_wav(self, midi_path, wav_path, gain=1.0):
        """Render MIDI file to WAV using FluidSynth"""
        try:
            cmd = [
                'fluidsynth',
                '-F', wav_path,
                '-r', str(self.sample_rate),
                '-g', str(gain),
                self.soundfont,
                midi_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"FluidSynth error: {result.stderr}")
                return False
                
            return os.path.exists(wav_path)
        except Exception as e:
            print(f"Error rendering MIDI: {e}")
            return False
    
    def load_audio(self, wav_path):
        """Load WAV file as float32 numpy array"""
        try:
            rate, data = wavfile.read(wav_path)
            
            # Convert to float32 and normalize
            if data.dtype == np.int16:
                data = data.astype(np.float32) / 32768.0
            elif data.dtype == np.int32:
                data = data.astype(np.float32) / 2147483648.0
            else:
                data = data.astype(np.float32)
            
            # Convert stereo to mono if needed (we'll process in mono, then stereo-ize later)
            if len(data.shape) > 1:
                data = data.mean(axis=1)
            
            return data, rate
        except Exception as e:
            print(f"Error loading audio: {e}")
            return None, None
    
    def save_audio(self, data, wav_path, rate=None):
        """Save float32 numpy array as WAV file"""
        if rate is None:
            rate = self.sample_rate
        
        # Ensure stereo output
        if len(data.shape) == 1:
            data = np.stack([data, data], axis=1)
        
        # Convert to int16
        data_int16 = np.clip(data * 32767, -32768, 32767).astype(np.int16)
        
        wavfile.write(wav_path, rate, data_int16)
    
    def apply_simple_compressor(self, audio, threshold=0.5, ratio=4.0, attack_ms=5, release_ms=50):
        """Simple envelope-following compressor"""
        attack_samples = int(attack_ms * self.sample_rate / 1000)
        release_samples = int(release_ms * self.sample_rate / 1000)
        
        envelope = np.abs(audio)
        
        # Smooth envelope
        envelope = np.maximum.accumulate(envelope)
        for i in range(1, len(envelope)):
            if envelope[i] > envelope[i-1]:
                envelope[i] = envelope[i-1] + (envelope[i] - envelope[i-1]) / attack_samples
            else:
                envelope[i] = envelope[i-1] + (envelope[i] - envelope[i-1]) / release_samples
        
        # Calculate gain reduction
        gain_reduction = np.ones_like(envelope)
        over_threshold = envelope > threshold
        gain_reduction[over_threshold] = threshold / envelope[over_threshold]
        gain_reduction[over_threshold] = 1 - (1 - gain_reduction[over_threshold]) / ratio
        
        return audio * gain_reduction
    
    def apply_soft_limiter(self, audio, ceiling=0.98):
        """Soft limiter to prevent clipping"""
        # Tanh-based soft clipping
        return np.tanh(audio / ceiling) * ceiling
    
    def normalize_loudness(self, audio, target_rms=-16):
        """Normalize audio to target RMS level (in dB)"""
        current_rms = np.sqrt(np.mean(audio ** 2))
        if current_rms > 0:
            target_linear = 10 ** (target_rms / 20)
            gain = target_linear / current_rms
            return audio * gain
        return audio
    
    def render_full_mix(self, midi_path, output_path, groove_type="STRAIGHT"):
        """
        Render complete MIDI file with mixing and mastering
        
        Args:
            midi_path: Path to MIDI file
            output_path: Path to output WAV file
            groove_type: Groove type for sidechain amount (CHILL, STRAIGHT, DRIVING)
        """
        print(f"Rendering: {midi_path}")
        print(f"Output: {output_path}")
        
        # Step 1: Render full MIDI to temp file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            # Render with FluidSynth
            if not self.render_midi_to_wav(midi_path, tmp_path, gain=1.2):
                print("Failed to render MIDI")
                return False
            
            # Load rendered audio
            audio, rate = self.load_audio(tmp_path)
            if audio is None:
                return False
            
            print(f"  Loaded audio: {len(audio)/rate:.2f}s, {rate}Hz")
            
            # Step 2: Apply master bus processing
            print("  Applying compression...")
            audio = self.apply_simple_compressor(audio, threshold=0.6, ratio=3.0)
            
            # Step 3: Normalize loudness
            print("  Normalizing loudness...")
            audio = self.normalize_loudness(audio, target_rms=-14)
            
            # Step 4: Soft limiter
            print("  Applying limiter...")
            audio = self.apply_soft_limiter(audio, ceiling=0.95)
            
            # Step 5: Save final output
            print(f"  Saving to: {output_path}")
            self.save_audio(audio, output_path)
            
            file_size = os.path.getsize(output_path) / (1024 * 1024)
            print(f"✅ Rendered successfully: {file_size:.1f}MB")
            
            return True
            
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


def main():
    if len(sys.argv) < 3:
        print("Usage: render_pipeline.py <input.mid> <output.wav> [groove_type]")
        print("  groove_type: CHILL, STRAIGHT, or DRIVING (default: STRAIGHT)")
        sys.exit(1)
    
    midi_path = sys.argv[1]
    output_path = sys.argv[2]
    groove_type = sys.argv[3] if len(sys.argv) > 3 else "STRAIGHT"
    
    if not os.path.exists(midi_path):
        print(f"Error: MIDI file not found: {midi_path}")
        sys.exit(1)
    
    pipeline = AudioRenderPipeline()
    success = pipeline.render_full_mix(midi_path, output_path, groove_type)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
