"""
Phase 9: Mix preset schema and loader
Defines dataclasses for genre-specific mixing presets loaded from YAML
"""

from dataclasses import dataclass, field
from typing import Dict, Optional
import yaml
import os
from pathlib import Path


@dataclass
class CompressorSettings:
    """Bus compressor settings"""
    threshold_db: float = -12.0
    ratio: float = 3.0
    attack_ms: float = 10.0
    release_ms: float = 120.0


@dataclass
class LimiterSettings:
    """Master limiter settings"""
    ceiling_db: float = -0.8


@dataclass
class BusPreset:
    """Bus-level effects and processing"""
    sidechain_amount: float = 0.3  # 0-1, amount of ducking
    stereo_widen: float = 0.15     # 0-1, stereo widening amount
    reverb_send: float = 0.1       # 0-1, reverb send level
    compressor: CompressorSettings = field(default_factory=CompressorSettings)
    limiter: LimiterSettings = field(default_factory=LimiterSettings)


@dataclass
class InstrumentPreset:
    """Per-instrument processing settings"""
    sound: str = "sf2://FluidR3/0"  # Soundfont reference or sample path
    hp_hz: float = 20.0              # High-pass filter frequency
    lp_hz: float = 20000.0           # Low-pass filter frequency
    reverb_send: float = 0.0         # Additional reverb send (0-1)
    delay_send: float = 0.0          # Delay send (0-1)
    gain_db: float = 0.0             # Gain adjustment


@dataclass
class MixPreset:
    """Complete mix preset for a genre"""
    name: str
    drum_kit: str                    # Name of drum kit to use
    target_lufs: float = -10.0       # Target integrated loudness
    bus: BusPreset = field(default_factory=BusPreset)
    instruments: Dict[str, InstrumentPreset] = field(default_factory=dict)


def load_mix_preset(preset_name: str, presets_dir: Optional[Path] = None) -> MixPreset:
    """
    Load a mix preset from YAML file
    
    Args:
        preset_name: Name of preset (e.g., 'rap', 'house', 'rnb')
        presets_dir: Optional custom directory (defaults to audio-producer/mix/presets/)
    
    Returns:
        MixPreset object
    
    Raises:
        FileNotFoundError: If preset file doesn't exist
        yaml.YAMLError: If preset file is invalid
    """
    if presets_dir is None:
        # Default to audio-producer/mix/presets/
        script_dir = Path(__file__).parent
        presets_dir = script_dir / 'presets'
    else:
        # Convert to Path if string
        presets_dir = Path(presets_dir)
    
    preset_path = presets_dir / f'{preset_name}.yaml'
    
    if not preset_path.exists():
        raise FileNotFoundError(f"Mix preset not found: {preset_path}")
    
    with open(preset_path, 'r') as f:
        data = yaml.safe_load(f)
    
    # Parse bus settings
    bus_data = data.get('bus', {})
    compressor_data = bus_data.get('compressor', {})
    limiter_data = bus_data.get('limiter', {})
    
    compressor = CompressorSettings(
        threshold_db=compressor_data.get('threshold_db', -12.0),
        ratio=compressor_data.get('ratio', 3.0),
        attack_ms=compressor_data.get('attack_ms', 10.0),
        release_ms=compressor_data.get('release_ms', 120.0)
    )
    
    limiter = LimiterSettings(
        ceiling_db=limiter_data.get('ceiling_db', -0.8)
    )
    
    bus = BusPreset(
        sidechain_amount=bus_data.get('sidechain_amount', 0.3),
        stereo_widen=bus_data.get('stereo_widen', 0.15),
        reverb_send=bus_data.get('reverb_send', 0.1),
        compressor=compressor,
        limiter=limiter
    )
    
    # Parse instrument settings
    instruments = {}
    instruments_data = data.get('instruments', {})
    
    for inst_name, inst_data in instruments_data.items():
        instruments[inst_name] = InstrumentPreset(
            sound=inst_data.get('sound', 'sf2://FluidR3/0'),
            hp_hz=inst_data.get('hp_hz', 20.0),
            lp_hz=inst_data.get('lp_hz', 20000.0),
            reverb_send=inst_data.get('reverb_send', 0.0),
            delay_send=inst_data.get('delay_send', 0.0),
            gain_db=inst_data.get('gain_db', 0.0)
        )
    
    return MixPreset(
        name=data['name'],
        drum_kit=data['drum_kit'],
        target_lufs=data.get('target_lufs', -10.0),
        bus=bus,
        instruments=instruments
    )


def get_preset_for_genre(genre: str, presets_dir: Optional[Path] = None) -> MixPreset:
    """
    Get appropriate mix preset for a genre
    
    Args:
        genre: Genre name (e.g., 'Rap', 'House', 'R&B', 'EDM Drop', 'EDM Chill')
        presets_dir: Optional custom directory (defaults to audio-producer/mix/presets/)
    
    Returns:
        MixPreset object
    """
    # Map genre names to preset names
    genre_map = {
        'Rap': 'rap',
        'rap': 'rap',
        'RAP': 'rap',
        'House': 'house',
        'house': 'house',
        'HOUSE': 'house',
        'R&B': 'rnb',
        'RnB': 'rnb',
        'rnb': 'rnb',
        'RNB': 'rnb',
        'EDM Drop': 'house',  # Use house preset for EDM Drop (similar energy)
        'EDM Chill': 'rnb',   # Use rnb preset for EDM Chill (softer)
        'EDM_DROP': 'house',
        'EDM_CHILL': 'rnb'
    }
    
    preset_name = genre_map.get(genre, 'house')  # Default to house
    return load_mix_preset(preset_name, presets_dir)


if __name__ == '__main__':
    # Test loading presets
    import sys
    
    print("Testing mix preset loader...\n")
    
    for preset_name in ['rap', 'house', 'rnb']:
        try:
            preset = load_mix_preset(preset_name)
            print(f"✓ Loaded preset: {preset.name}")
            print(f"  Drum kit: {preset.drum_kit}")
            print(f"  Target LUFS: {preset.target_lufs}")
            print(f"  Sidechain: {preset.bus.sidechain_amount}")
            print(f"  Instruments: {list(preset.instruments.keys())}")
            print()
        except Exception as e:
            print(f"✗ Failed to load {preset_name}: {e}")
            sys.exit(1)
    
    print("All presets loaded successfully!")
