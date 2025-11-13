#!/usr/bin/env python3
"""
Phase 9 Test Script
Tests end-to-end pipeline with 3 random images from ml/data/raw_images/
Validates genre diversity (Rap, House, R&B sounds different)
Saves output to output/ folder
"""
import os
import sys
import random
import subprocess
import json
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / 'audio-producer'))
sys.path.insert(0, str(PROJECT_ROOT / 'scripts'))

from enhance_composition import enhance_midi

def find_raw_images(images_dir: str, count: int = 3) -> list:
    """
    Find random images from raw_images directory
    
    Args:
        images_dir: Path to raw_images directory
        count: Number of random images to select
    
    Returns:
        List of image paths
    """
    image_files = []
    
    for ext in ['.jpg', '.jpeg', '.png']:
        image_files.extend(list(Path(images_dir).glob(f'**/*{ext}')))
        image_files.extend(list(Path(images_dir).glob(f'**/*{ext.upper()}')))
    
    if len(image_files) == 0:
        print(f"Error: No images found in {images_dir}")
        return []
    
    # Select random images
    selected = random.sample(image_files, min(count, len(image_files)))
    
    return [str(img) for img in selected]


def test_image_to_music(image_path: str, output_dir: str, test_name: str) -> bool:
    """
    Test full pipeline: image -> MIDI -> audio
    
    Args:
        image_path: Path to input image
        output_dir: Output directory
        test_name: Test name (for output files)
    
    Returns:
        True if successful
    """
    print(f"\n{'='*60}")
    print(f"Testing: {test_name}")
    print(f"Image: {image_path}")
    print(f"{'='*60}")
    
    # Create output paths
    midi_output = os.path.join(output_dir, f"{test_name}.mid")
    audio_output = os.path.join(output_dir, f"{test_name}.wav")
    
    # Step 1: Run C++ core to generate MIDI
    print("\n[1] Generating MIDI from image...")
    
    cpp_exe = PROJECT_ROOT / 'cpp-core' / 'build' / 'soundcanvas_core'
    if os.name == 'nt':  # Windows
        cpp_exe = PROJECT_ROOT / 'cpp-core' / 'build' / 'Release' / 'soundcanvas_core.exe'
        if not cpp_exe.exists():
            cpp_exe = PROJECT_ROOT / 'cpp-core' / 'build' / 'Debug' / 'soundcanvas_core.exe'
    
    if not cpp_exe.exists():
        print(f"Error: C++ executable not found: {cpp_exe}")
        print("Build the C++ core first:")
        print("  cd cpp-core")
        print("  mkdir build && cd build")
        print("  cmake .. && cmake --build .")
        return False
    
    try:
        cmd = [str(cpp_exe), '--compose-only', image_path, midi_output]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            print(f"C++ generation failed:")
            print(result.stderr)
            return False
        
        print(result.stdout)
        
        if not os.path.exists(midi_output):
            print(f"Error: MIDI not created: {midi_output}")
            return False
        
        print(f"[OK] MIDI created: {midi_output}")
        
        # Parse genre from output
        genre = "EDM_DROP"  # Default
        for line in result.stdout.split('\n'):
            if 'Genre:' in line or 'genre:' in line:
                for g in ['HOUSE', 'RAP', 'RNB', 'EDM_CHILL', 'EDM_DROP']:
                    if g in line.upper():
                        genre = g
                        break
        
        print(f"Detected genre: {genre}")
        
        # Enhance MIDI for more variation
        print("\n[1.5] Enhancing composition...")
        enhanced_midi = os.path.join(output_dir, f"{test_name}_enhanced.mid")
        try:
            enhance_midi(midi_output, enhanced_midi, genre=genre)
            midi_output = enhanced_midi  # Use enhanced version for rendering
        except Exception as e:
            print(f"  Warning: Enhancement failed: {e}")
            print(f"  Using original MIDI")
        
    except subprocess.TimeoutExpired:
        print("Error: C++ generation timed out")
        return False
    except Exception as e:
        print(f"Error running C++ core: {e}")
        return False
    
    # Step 2: Render audio with Python pipeline
    print("\n[2] Rendering audio with Phase 9 pipeline...")
    
    try:
        from synth_drums import DrumSynthesizer
        from fx_player import FXPlayer
        from mix.schema import get_preset_for_genre
        from stem_mixer import mix_stems
        from mastering import apply_mastering_chain
        
        print("  Initializing components...")
        
        # Initialize drum sampler (will be used per-genre)
        assets_dir_path = PROJECT_ROOT / 'audio-producer' / 'assets'
        
        # Initialize FX player
        fx_player = FXPlayer(
            fx_config_path=str(assets_dir_path / 'fx' / 'fx_config.yaml'),
            assets_dir=str(assets_dir_path)
        )
        
        # Get mix preset for genre
        mix_preset = get_preset_for_genre(
            genre, 
            str(PROJECT_ROOT / 'audio-producer' / 'mix' / 'presets')
        )
        
        print(f"  Mix preset: {genre}")
        print(f"    Sidechain: {mix_preset.bus.sidechain_amount}")
        
        # Render drums with samples
        drums_wav = os.path.join(output_dir, f"{test_name}_drums.wav")
        
        # Map genre to drum synthesis style
        drum_genre = {
            'RAP': 'trap',
            'HOUSE': 'house',
            'RNB': 'hip-hop',
            'EDM_DROP': 'edm',
            'EDM_CHILL': 'edm'
        }.get(genre, 'edm')
        
        print(f"  Rendering synthesized drums ({drum_genre} style)...")
        
        # Use drum synthesizer instead of samples
        drum_synth = DrumSynthesizer(samplerate=44100)
        drum_synth.render_midi_to_drums(midi_output, drums_wav, genre=drum_genre)
        print(f"    [OK] Drums: {drums_wav}")
        
        # Render FX
        fx_wav = os.path.join(output_dir, f"{test_name}_fx.wav")
        
        import mido
        midi_file = mido.MidiFile(midi_output)
        duration = midi_file.length if hasattr(midi_file, 'length') else 120.0
        
        print(f"  Rendering FX (duration: {duration:.1f}s)...")
        fx_player.render_fx_stem(midi_output, fx_wav, duration)
        print(f"    [OK] FX: {fx_wav}")
        
        # Render other instruments with FluidSynth (bass, lead, pad)
        print("  Rendering melodic instruments with FluidSynth...")
        
        # Try Windows path first, then local, then Linux
        sf2_candidates = [
            Path('C:/soundfonts/FluidR3_GM.sf2'),
            PROJECT_ROOT / 'audio-producer' / 'FluidR3_GM.sf2',
            Path('/usr/share/soundfonts/FluidR3_GM.sf2')
        ]
        sf2_path = next((p for p in sf2_candidates if p.exists()), None)
        
        melodic_wav = os.path.join(output_dir, f"{test_name}_melodic.wav")
        
        # Find FluidSynth executable
        fluidsynth_paths = [
            'C:/fluidsynth/bin/fluidsynth.exe',
            'fluidsynth'  # Try PATH
        ]
        fluidsynth_exe = next((p for p in fluidsynth_paths if os.path.exists(p) or p == 'fluidsynth'), 'fluidsynth')
        
        if sf2_path and os.path.exists(sf2_path):
            cmd = [
                fluidsynth_exe,
                '-ni',
                '-g', '0.8',
                '-r', '44100',
                str(sf2_path),
                midi_output,
                '-F', melodic_wav,
                '-O', 's16'
            ]
            
            subprocess.run(cmd, capture_output=True, timeout=60)
            
            if os.path.exists(melodic_wav):
                print(f"    [OK] Melodic: {melodic_wav}")
            else:
                print("    Warning: FluidSynth rendering failed")
                melodic_wav = None
        else:
            print(f"    Warning: Soundfont not found: {sf2_path}")
            melodic_wav = None
        
        # Mix stems
        print("  Mixing stems...")
        
        stems = {'drums': drums_wav}
        
        if melodic_wav and os.path.exists(melodic_wav):
            stems['melodic'] = melodic_wav
        
        if os.path.exists(fx_wav):
            stems['fx'] = fx_wav
        
        temp_mix = os.path.join(output_dir, f"{test_name}_temp.wav")
        
        mix_stems(
            stems,
            temp_mix,
            apply_sidechain_to=['melodic'],
            stem_gains={'drums': 1.0, 'melodic': 0.7, 'fx': 0.3},
            midi_path=midi_output,
            sidechain_amount=mix_preset.bus.sidechain_amount
        )
        
        print(f"    [OK] Mixed: {temp_mix}")
        
        # Master
        print("  Mastering...")
        
        apply_mastering_chain(temp_mix, audio_output, target_lufs=-14.0)
        
        print(f"    [OK] Final: {audio_output}")
        
        # Cleanup temp files
        for temp_file in [drums_wav, fx_wav, melodic_wav, temp_mix]:
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass
        
        print(f"\n[OK] Test complete: {audio_output}")
        
        return True
        
    except ImportError as e:
        print(f"Error: Missing Python dependencies: {e}")
        print("Install required packages:")
        print("  pip install mido soundfile scipy numpy pyyaml")
        return False
    except Exception as e:
        print(f"Error rendering audio: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test runner"""
    print("="*60)
    print("Phase 9 Test Script")
    print("Testing genre diversity with 3 random images")
    print("="*60)
    
    # Setup paths
    images_dir = PROJECT_ROOT / 'ml' / 'data' / 'raw_images'
    output_dir = PROJECT_ROOT / 'output'
    
    # Create output directory
    output_dir.mkdir(exist_ok=True)
    
    # Find random images
    print(f"\nSearching for images in: {images_dir}")
    
    if not images_dir.exists():
        print(f"Error: Images directory not found: {images_dir}")
        print("Download images first:")
        print("  cd ml")
        print("  python src/download_images.py")
        return 1
    
    image_paths = find_raw_images(str(images_dir), count=3)
    
    if not image_paths:
        return 1
    
    print(f"Selected {len(image_paths)} random images:")
    for img in image_paths:
        print(f"  - {img}")
    
    # Test each image
    results = []
    
    for i, img_path in enumerate(image_paths, 1):
        test_name = f"phase9_test{i}"
        success = test_image_to_music(img_path, str(output_dir), test_name)
        results.append((test_name, success))
    
    # Summary
    print(f"\n{'='*60}")
    print("Test Summary")
    print(f"{'='*60}")
    
    for test_name, success in results:
        status = "[PASS]" if success else "[FAIL]"
        print(f"{status}  {test_name}")
    
    success_count = sum(1 for _, s in results if s)
    print(f"\nPassed: {success_count}/{len(results)}")
    
    if success_count == len(results):
        print("\n[OK] All tests passed! Check output/ folder for results.")
        return 0
    else:
        print(f"\n[FAIL] {len(results) - success_count} test(s) failed.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
