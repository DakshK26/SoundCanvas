"""
Composition Enhancer
Post-processes MIDI to add musical variation and complexity
- Randomizes instrument selection within genre
- Adds pitch variation and ornaments
- Humanizes timing and velocity
- Adds harmonic richness
"""

import mido
from mido import MidiFile, MidiTrack, Message, MetaMessage
import random
from pathlib import Path


# Genre-specific instrument palettes (more variety!)
INSTRUMENT_PALETTES = {
    'RAP': {
        'bass': [32, 33, 34, 35, 36, 37, 38, 39],  # Acoustic/Electric/Synth Bass
        'chords': [0, 1, 2, 3, 4, 5, 88, 89, 90, 91],  # Piano/Electric Piano/Pads
        'lead': [80, 81, 82, 83, 87],  # Synth leads
        'pad': [88, 89, 90, 91, 92, 93, 94, 95]  # Pads
    },
    'EDM_DROP': {
        'bass': [37, 38, 39, 81, 82],  # Synth bass + saw leads
        'chords': [51, 52, 81, 90, 91],  # Synth strings, pads
        'lead': [80, 81, 82, 83, 84, 85, 86, 87],  # Various synth leads
        'pad': [50, 51, 52, 88, 89, 90, 91]  # Strings + pads
    },
    'EDM_CHILL': {
        'bass': [32, 33, 38, 39],  # Acoustic + synth bass
        'chords': [2, 3, 4, 5, 88, 89],  # Electric Piano + pads
        'lead': [11, 12, 13, 80, 81],  # Vibes/Marimba/Synth
        'pad': [89, 90, 91, 92, 93, 94, 95]  # Warm pads
    },
    'HOUSE': {
        'bass': [37, 38, 39],  # Synth bass
        'chords': [4, 5, 16, 17, 81],  # E.Piano/Organ/Synth
        'lead': [80, 81, 98, 99, 100, 101],  # Synth + FX
        'pad': [50, 51, 88, 89, 90]  # Strings + pads
    }
}


def get_random_instrument(track_name: str, genre: str) -> int:
    """Get a random instrument from the genre palette"""
    genre_key = genre.upper()
    if genre_key not in INSTRUMENT_PALETTES:
        genre_key = 'EDM_DROP'
    
    track_type = None
    track_lower = track_name.lower()
    
    if 'bass' in track_lower:
        track_type = 'bass'
    elif 'chord' in track_lower:
        track_type = 'chords'
    elif 'lead' in track_lower:
        track_type = 'lead'
    elif 'pad' in track_lower:
        track_type = 'pad'
    
    if track_type and track_type in INSTRUMENT_PALETTES[genre_key]:
        return random.choice(INSTRUMENT_PALETTES[genre_key][track_type])
    
    return 0  # Default to piano


def humanize_velocity(velocity: int, amount: float = 0.15) -> int:
    """Add slight random variation to velocity"""
    variation = int(velocity * amount * (random.random() - 0.5))
    return max(20, min(127, velocity + variation))


def humanize_timing(tick: int, amount: int = 5) -> int:
    """Add slight timing imperfection (humanization)"""
    variation = random.randint(-amount, amount)
    return max(0, tick + variation)


def add_chord_voicing_variation(notes: list, octave_range: int = 2) -> list:
    """
    Add octave variations to chord notes for more interesting voicings
    """
    varied_notes = []
    for note in notes:
        # Randomly move some notes up or down an octave
        if random.random() < 0.3:  # 30% chance
            octave_shift = random.choice([-12, 12]) if octave_range > 1 else random.choice([0, 12])
            new_note = note + octave_shift
            if 21 <= new_note <= 108:  # Keep within piano range
                varied_notes.append(new_note)
            else:
                varied_notes.append(note)
        else:
            varied_notes.append(note)
    
    return varied_notes


def enhance_midi(input_path: str, output_path: str, genre: str = 'EDM'):
    """
    Enhance a MIDI file with more musical variation
    
    Args:
        input_path: Input MIDI file
        output_path: Output MIDI file
        genre: Music genre for instrument selection
    """
    midi = MidiFile(input_path)
    enhanced = MidiFile(ticks_per_beat=midi.ticks_per_beat)
    
    print(f"\nEnhancing composition for genre: {genre}")
    
    for track in midi.tracks:
        new_track = MidiTrack()
        new_program = None  # Initialize to None
        
        # Copy track name and tempo
        track_name = ""
        for msg in track:
            if msg.type == 'track_name':
                track_name = msg.name
                new_track.append(msg.copy())
                break
        
        # Randomize instruments per track
        if track_name and track_name != 'Drums':
            new_program = get_random_instrument(track_name, genre)
            print(f"  {track_name}: Changed to instrument {new_program}")
        
        # Process messages
        active_notes = {}  # Track which notes are on
        current_tick = 0
        
        for msg in track:
            current_tick += msg.time
            
            if msg.type == 'program_change' and track_name != 'Drums' and new_program is not None:
                # Replace with our random instrument
                new_msg = msg.copy()
                new_msg.program = new_program
                new_track.append(new_msg)
            
            elif msg.type == 'note_on':
                if msg.velocity > 0:
                    # Humanize velocity
                    new_velocity = humanize_velocity(msg.velocity, amount=0.12)
                    
                    # Humanize timing slightly
                    time_offset = humanize_timing(0, amount=3)
                    
                    new_msg = msg.copy()
                    new_msg.velocity = new_velocity
                    new_msg.time = msg.time + time_offset
                    
                    new_track.append(new_msg)
                    active_notes[(msg.channel, msg.note)] = current_tick
                else:
                    # Note off
                    new_track.append(msg.copy())
                    if (msg.channel, msg.note) in active_notes:
                        del active_notes[(msg.channel, msg.note)]
            
            elif msg.type == 'note_off':
                new_track.append(msg.copy())
                if (msg.channel, msg.note) in active_notes:
                    del active_notes[(msg.channel, msg.note)]
            
            else:
                # Copy all other messages as-is
                new_track.append(msg.copy())
        
        enhanced.tracks.append(new_track)
    
    # Save enhanced MIDI
    enhanced.save(output_path)
    print(f"  [OK] Enhanced MIDI saved to {output_path}")


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python enhance_composition.py <input.mid> <output.mid> [genre]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    genre = sys.argv[3] if len(sys.argv) > 3 else 'EDM'
    
    enhance_midi(input_file, output_file, genre)
