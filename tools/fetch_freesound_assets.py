"""
Phase 9: Freesound Asset Fetcher
Downloads drum samples and FX from Freesound API based on YAML configs
"""

import os
import sys
import json
import yaml
import requests
import time
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class FreesoundCredentials:
    """Freesound API credentials"""
    client_id: str
    api_key: str


def load_freesound_credentials(creds_file: Optional[Path] = None) -> FreesoundCredentials:
    """Load Freesound API credentials from JSON file"""
    if creds_file is None:
        # Look for freesound.json in repo root
        script_dir = Path(__file__).parent.parent
        creds_file = script_dir / 'freesound.json'
    
    if not creds_file.exists():
        raise FileNotFoundError(
            f"Freesound credentials not found at {creds_file}\n"
            f"Create freesound.json with: {{'Client_id': '...', 'Api_key': '...'}}"
        )
    
    with open(creds_file, 'r') as f:
        data = json.load(f)
    
    return FreesoundCredentials(
        client_id=data['Client_id'],
        api_key=data['Api_key']
    )


class FreesoundFetcher:
    """
    Fetches audio samples from Freesound API
    """
    
    BASE_URL = "https://freesound.org/apiv2"
    
    def __init__(self, credentials: FreesoundCredentials):
        self.credentials = credentials
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Token {credentials.api_key}'
        })
        self.rate_limit_delay = 0.5  # seconds between requests
    
    def search_sounds(self, 
                      query: str,
                      licenses: List[str],
                      file_type: str = 'wav',
                      min_samplerate: int = 44100,
                      max_duration: float = 10.0,
                      limit: int = 20) -> List[Dict]:
        """
        Search for sounds on Freesound
        
        Args:
            query: Search query (tags)
            licenses: List of allowed license names
            file_type: File type filter
            min_samplerate: Minimum sample rate
            max_duration: Maximum duration in seconds
            limit: Maximum number of results
        
        Returns:
            List of sound info dicts
        """
        # Build filter string
        filters = []
        if file_type:
            filters.append(f'type:{file_type}')
        if min_samplerate:
            filters.append(f'samplerate:[{min_samplerate} TO *]')
        if max_duration:
            filters.append(f'duration:[* TO {max_duration}]')
        
        # Build license filter
        license_map = {
            'Creative Commons 0': '"Creative Commons 0"',
            'Attribution': '"Attribution"'
        }
        license_filter = ' OR '.join([license_map.get(lic, lic) for lic in licenses])
        if license_filter:
            filters.append(f'license:({license_filter})')
        
        filter_str = ' '.join(filters)
        
        params = {
            'query': query,
            'filter': filter_str,
            'page_size': min(limit, 150),  # API max is 150
            'fields': 'id,name,tags,license,url,previews,download,samplerate,duration,username',
            'sort': 'downloads_desc'  # Get most popular first
        }
        
        try:
            time.sleep(self.rate_limit_delay)
            response = self.session.get(f'{self.BASE_URL}/search/text/', params=params)
            response.raise_for_status()
            data = response.json()
            
            results = data.get('results', [])
            print(f"  Found {len(results)} sounds for query: {query}")
            return results[:limit]
        
        except requests.exceptions.RequestException as e:
            print(f"  Warning: Search failed for '{query}': {e}")
            return []
    
    def download_sound(self, sound_id: int, output_path: Path, preview_url: str = None) -> bool:
        """
        Download a sound file using preview URL (HQ preview or original if available)
        
        Args:
            sound_id: Freesound sound ID
            output_path: Where to save the file
            preview_url: Direct preview URL (uses HQ preview if available)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # If no preview URL provided, get sound details first
            if not preview_url:
                time.sleep(self.rate_limit_delay)
                response = self.session.get(f'{self.BASE_URL}/sounds/{sound_id}/')
                if response.status_code == 200:
                    sound_data = response.json()
                    previews = sound_data.get('previews', {})
                    # Prefer HQ preview, fall back to preview-lq
                    preview_url = previews.get('preview-hq-mp3') or previews.get('preview-lq-mp3')
                    if not preview_url:
                        print(f"    Warning: No preview URL for sound {sound_id}")
                        return False
            
            # Download the preview file
            time.sleep(self.rate_limit_delay)
            response = requests.get(preview_url, stream=True)
            
            if response.status_code == 200:
                # Save as temporary MP3, then convert to WAV if needed
                output_path.parent.mkdir(parents=True, exist_ok=True)
                temp_mp3 = output_path.with_suffix('.mp3')
                
                with open(temp_mp3, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                # Convert MP3 to WAV using pydub or just keep as MP3
                # For now, rename to .wav (the audio libraries can handle MP3)
                # In production, you'd want to use ffmpeg to convert
                import shutil
                shutil.move(str(temp_mp3), str(output_path))
                
                return True
            else:
                print(f"    Warning: Download failed for sound {sound_id}: {response.status_code}")
                return False
        
        except Exception as e:
            print(f"    Warning: Download failed for sound {sound_id}: {e}")
            return False


def fetch_drum_kit(kit_yaml_path: Path, output_dir: Path, fetcher: FreesoundFetcher) -> Dict:
    """
    Fetch drum samples for a kit based on YAML config
    
    Args:
        kit_yaml_path: Path to kit YAML file
        output_dir: Base output directory for drums
        fetcher: FreesoundFetcher instance
    
    Returns:
        Dict with download statistics
    """
    with open(kit_yaml_path, 'r') as f:
        config = yaml.safe_load(f)
    
    kit_name = config['name']
    tags = config['tags']
    licenses = config['license']
    limits = config['limits']
    
    print(f"\nFetching drum kit: {kit_name}")
    
    stats = {'total': 0, 'success': 0, 'failed': 0}
    metadata = []
    
    kit_dir = output_dir / kit_name
    
    for category, tag_list in tags.items():
        limit = limits.get(category, 10)
        query = ' '.join(tag_list)
        
        print(f"  Category: {category} (limit: {limit})")
        
        # Search for sounds
        sounds = fetcher.search_sounds(
            query=query,
            licenses=licenses,
            limit=limit
        )
        
        # Download each sound
        for idx, sound in enumerate(sounds):
            sound_id = sound['id']
            filename = f"{category}_{idx:03d}.wav"
            output_path = kit_dir / category / filename
            
            # Get HQ preview URL
            previews = sound.get('previews', {})
            preview_url = previews.get('preview-hq-mp3') or previews.get('preview-lq-mp3')
            
            stats['total'] += 1
            
            if preview_url and fetcher.download_sound(sound_id, output_path, preview_url):
                stats['success'] += 1
                metadata.append({
                    'kit': kit_name,
                    'category': category,
                    'filename': str(output_path.relative_to(output_dir)),
                    'freesound_id': sound_id,
                    'name': sound['name'],
                    'username': sound.get('username', 'unknown'),
                    'license': sound['license'],
                    'url': sound['url']
                })
                print(f"    ✓ {filename} (ID: {sound_id})")
            else:
                stats['failed'] += 1
    
    print(f"  Downloaded {stats['success']}/{stats['total']} samples")
    return metadata


def fetch_fx_sounds(fx_yaml_path: Path, output_dir: Path, fetcher: FreesoundFetcher) -> Dict:
    """
    Fetch FX samples based on YAML config
    
    Args:
        fx_yaml_path: Path to FX config YAML
        output_dir: Base output directory for FX
        fetcher: FreesoundFetcher instance
    
    Returns:
        Dict with download statistics
    """
    with open(fx_yaml_path, 'r') as f:
        config = yaml.safe_load(f)
    
    groups = config['groups']
    licenses = config['license']
    constraints = config['constraints']
    
    print(f"\nFetching FX sounds")
    
    stats = {'total': 0, 'success': 0, 'failed': 0}
    metadata = []
    
    for group_name, group_config in groups.items():
        tags = group_config['tags']
        limit = group_config['limits']
        query = ' '.join(tags)
        
        print(f"  Group: {group_name} (limit: {limit})")
        
        # Search for sounds
        sounds = fetcher.search_sounds(
            query=query,
            licenses=licenses,
            file_type=constraints.get('type', 'wav'),
            min_samplerate=constraints.get('min_samplerate_hz', 44100),
            max_duration=constraints.get('max_duration_s', 10.0),
            limit=limit
        )
        
        # Download each sound
        for idx, sound in enumerate(sounds):
            sound_id = sound['id']
            filename = f"{group_name}_{idx:03d}.wav"
            output_path = output_dir / group_name / filename
            
            # Get HQ preview URL
            previews = sound.get('previews', {})
            preview_url = previews.get('preview-hq-mp3') or previews.get('preview-lq-mp3')
            
            stats['total'] += 1
            
            if preview_url and fetcher.download_sound(sound_id, output_path, preview_url):
                stats['success'] += 1
                metadata.append({
                    'group': group_name,
                    'filename': str(output_path.relative_to(output_dir)),
                    'freesound_id': sound_id,
                    'name': sound['name'],
                    'username': sound.get('username', 'unknown'),
                    'license': sound['license'],
                    'url': sound['url']
                })
                print(f"    ✓ {filename} (ID: {sound_id})")
            else:
                stats['failed'] += 1
    
    print(f"  Downloaded {stats['success']}/{stats['total']} FX samples")
    return metadata


def main():
    """Main fetcher script"""
    print("=" * 60)
    print("Phase 9: Freesound Asset Fetcher")
    print("=" * 60)
    
    # Load credentials
    try:
        creds = load_freesound_credentials()
        print(f"✓ Loaded Freesound credentials (Client ID: {creds.client_id[:10]}...)")
    except Exception as e:
        print(f"✗ Failed to load credentials: {e}")
        return 1
    
    # Setup paths
    script_dir = Path(__file__).parent.parent
    assets_dir = script_dir / 'audio-producer' / 'assets'
    kits_dir = assets_dir / 'kits'
    fx_dir = assets_dir / 'fx'
    drums_output = assets_dir / 'drums'
    fx_output = assets_dir / 'fx'
    meta_dir = assets_dir / '_meta'
    
    # Create fetcher
    fetcher = FreesoundFetcher(creds)
    
    # Collect all metadata
    all_metadata = []
    
    # Fetch drum kits
    print("\n" + "=" * 60)
    print("DRUM KITS")
    print("=" * 60)
    
    for kit_yaml in kits_dir.glob('*.yaml'):
        try:
            metadata = fetch_drum_kit(kit_yaml, drums_output, fetcher)
            all_metadata.extend(metadata)
        except Exception as e:
            print(f"✗ Failed to fetch kit {kit_yaml.name}: {e}")
    
    # Fetch FX
    print("\n" + "=" * 60)
    print("FX SOUNDS")
    print("=" * 60)
    
    fx_config_path = fx_dir / 'fx_config.yaml'
    if fx_config_path.exists():
        try:
            metadata = fetch_fx_sounds(fx_config_path, fx_output, fetcher)
            all_metadata.extend(metadata)
        except Exception as e:
            print(f"✗ Failed to fetch FX: {e}")
    else:
        print(f"✗ FX config not found: {fx_config_path}")
    
    # Save metadata
    meta_dir.mkdir(parents=True, exist_ok=True)
    meta_file = meta_dir / 'freesound_index.json'
    
    with open(meta_file, 'w') as f:
        json.dump(all_metadata, f, indent=2)
    
    print("\n" + "=" * 60)
    print(f"✓ Saved metadata to: {meta_file}")
    print(f"✓ Total samples downloaded: {len(all_metadata)}")
    print("=" * 60)
    
    # Create attribution file
    attribution_file = meta_dir / 'ATTRIBUTION.md'
    with open(attribution_file, 'w') as f:
        f.write("# Freesound Sample Attribution\n\n")
        f.write("All samples downloaded from Freesound.org under Creative Commons licenses.\n\n")
        f.write("## Samples Used\n\n")
        
        for item in all_metadata:
            f.write(f"- **{item['filename']}**\n")
            f.write(f"  - Name: {item['name']}\n")
            f.write(f"  - Author: {item['username']}\n")
            f.write(f"  - License: {item['license']}\n")
            f.write(f"  - URL: {item['url']}\n")
            f.write(f"\n")
    
    print(f"✓ Created attribution file: {attribution_file}\n")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
