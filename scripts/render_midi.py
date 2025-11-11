#!/usr/bin/env python3
"""
Simple MIDI to WAV renderer using mido and numpy
Renders MIDI to audio using basic synthesis
"""
import sys
import numpy as np
from scipy.io import wavfile
import subprocess
import os

def midi_to_wav_with_timidity(midi_path, wav_path):
    """Use timidity if available"""
    try:
        subprocess.run(['timidity', midi_path, '-Ow', '-o', wav_path], 
                      check=True, capture_output=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def midi_to_wav_with_fluidsynth(midi_path, wav_path):
    """Use fluidsynth if available"""
    try:
        # Try to find a soundfont
        soundfonts = [
            '/usr/share/soundfonts/default.sf2',
            '/usr/share/soundfonts/FluidR3_GM.sf2',
            '/System/Library/Components/CoreAudio.component/Contents/Resources/gs_instruments.dls'
        ]
        
        sf2 = None
        for sf in soundfonts:
            if os.path.exists(sf):
                sf2 = sf
                break
        
        if not sf2:
            return False
        
        subprocess.run(['fluidsynth', '-ni', sf2, midi_path, '-F', wav_path, '-r', '44100'],
                      check=True, capture_output=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def simple_synth_render(midi_path, wav_path):
    """Fallback: Simple synthesis using mido + numpy"""
    try:
        import mido
        
        print("Using simple synthesis (no soundfont)...")
        
        # Load MIDI
        mid = mido.MidiFile(midi_path)
        
        # Calculate duration
        duration = mid.length
        sample_rate = 44100
        num_samples = int(duration * sample_rate)
        
        # Generate audio
        audio = np.zeros(num_samples, dtype=np.float32)
        
        # Simple additive synthesis
        time = 0
        active_notes = {}
        
        for msg in mid:
            time += msg.time
            sample_pos = int(time * sample_rate)
            
            if msg.type == 'note_on' and msg.velocity > 0:
                # Start note
                active_notes[msg.note] = {
                    'start': sample_pos,
                    'velocity': msg.velocity / 127.0
                }
            elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                # End note
                if msg.note in active_notes:
                    start = active_notes[msg.note]['start']
                    velocity = active_notes[msg.note]['velocity']
                    
                    # Generate note sound
                    note_duration = sample_pos - start
                    if note_duration > 0 and start < num_samples:
                        end = min(sample_pos, num_samples)
                        t = np.arange(note_duration) / sample_rate
                        
                        # MIDI note to frequency
                        freq = 440 * (2 ** ((msg.note - 69) / 12))
                        
                        # Simple sine wave with ADSR envelope
                        attack = int(0.01 * sample_rate)
                        decay = int(0.1 * sample_rate)
                        release = int(0.2 * sample_rate)
                        
                        envelope = np.ones(len(t))
                        if len(t) > attack:
                            envelope[:attack] = np.linspace(0, 1, attack)
                        if len(t) > attack + decay:
                            envelope[attack:attack+decay] = np.linspace(1, 0.7, decay)
                        if len(t) > release:
                            envelope[-release:] = np.linspace(envelope[-release], 0, release)
                        
                        # Generate tone
                        tone = np.sin(2 * np.pi * freq * t) * envelope * velocity * 0.3
                        
                        # Add to audio
                        audio[start:end] += tone[:end-start]
                    
                    del active_notes[msg.note]
        
        # Normalize and save
        audio = np.clip(audio, -1, 1)
        audio_int16 = (audio * 32767).astype(np.int16)
        wavfile.write(wav_path, sample_rate, audio_int16)
        
        return True
        
    except Exception as e:
        print(f"Simple synth error: {e}")
        return False

def render_midi(midi_path, wav_path):
    """Try multiple rendering methods"""
    
    if not os.path.exists(midi_path):
        print(f"Error: MIDI file not found: {midi_path}")
        return False
    
    print(f"Rendering: {midi_path}")
    print(f"Output: {wav_path}")
    print()
    
    # Try timidity first (best quality)
    print("Trying timidity...")
    if midi_to_wav_with_timidity(midi_path, wav_path):
        print("✅ Rendered with timidity")
        return True
    
    # Try fluidsynth
    print("Trying fluidsynth...")
    if midi_to_wav_with_fluidsynth(midi_path, wav_path):
        print("✅ Rendered with fluidsynth")
        return True
    
    # Fallback to simple synthesis
    print("Trying simple synthesis...")
    if simple_synth_render(midi_path, wav_path):
        print("✅ Rendered with simple synthesis")
        print("Note: Basic quality - install fluidsynth for better sound")
        return True
    
    print("❌ All rendering methods failed")
    print("\nTo install rendering tools:")
    print("  brew install fluidsynth  # or")
    print("  brew install timidity")
    return False

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: render_midi.py <input.mid> <output.wav>")
        sys.exit(1)
    
    midi_path = sys.argv[1]
    wav_path = sys.argv[2]
    
    if render_midi(midi_path, wav_path):
        print(f"\n🎵 Audio ready: {wav_path}")
        print(f"Play with: afplay {wav_path}")
        sys.exit(0)
    else:
        sys.exit(1)
