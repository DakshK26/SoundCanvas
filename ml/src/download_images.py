"""
Download images from Kaggle using the Kaggle API.
Dataset: Landscape Pictures (4,319 images, ~700MB)
We'll use 3,000 images for training (subset extraction)

NO API KEYS IN THIS FILE - Kaggle reads from ~/.kaggle/kaggle.json automatically
"""
import os
import shutil
from pathlib import Path
import zipfile
import subprocess
import random

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "raw_images"
DATASET_NAME = "arnaud58/landscape-pictures"
TARGET_IMAGE_COUNT = 3000

def setup_kaggle_instructions():
    """
    Show instructions for setting up Kaggle API.
    """
    print("\n" + "="*70)
    print("🔑 KAGGLE API SETUP INSTRUCTIONS")
    print("="*70)
    print("\n1. Go to: https://www.kaggle.com/settings")
    print("2. Scroll down to 'API' section")
    print("3. Click 'Create New API Token'")
    print("4. This downloads 'kaggle.json' to your Downloads folder")
    print("\n5. Run these commands in terminal:")
    print("   mkdir -p ~/.kaggle")
    print("   mv ~/Downloads/kaggle.json ~/.kaggle/")
    print("   chmod 600 ~/.kaggle/kaggle.json")
    print("\n6. Install Kaggle CLI:")
    print("   pip3 install kaggle")
    print("\n7. Then run this script again with option 2")
    print("="*70 + "\n")

def check_kaggle_setup():
    """Check if Kaggle API is properly configured."""
    kaggle_json = Path.home() / ".kaggle" / "kaggle.json"
    
    if not kaggle_json.exists():
        return False, "kaggle.json not found in ~/.kaggle/"
    
    # Check if kaggle CLI is installed
    try:
        result = subprocess.run(["kaggle", "--version"], capture_output=True, text=True)
        if result.returncode != 0:
            return False, "Kaggle CLI not installed. Run: pip3 install kaggle"
    except FileNotFoundError:
        return False, "Kaggle CLI not installed. Run: pip3 install kaggle"
    
    return True, "Kaggle API is set up correctly!"

def download_kaggle_dataset():
    """
    Download the dataset using Kaggle API and select 3000 images.
    """
    # Check setup
    is_setup, message = check_kaggle_setup()
    
    if not is_setup:
        print(f"\n❌ {message}")
        print("\nPlease complete the setup first (run option 1)")
        return
    
    print(f"\n✅ {message}")
    print(f"\n📥 Downloading dataset: {DATASET_NAME}")
    print(f"📦 Size: ~700MB (4,319 landscape images)")
    print(f"🎯 Target: {TARGET_IMAGE_COUNT} images for training")
    print("⏳ This will take 2-5 minutes\n")
    
    # Confirm download
    confirm = input("Continue with download? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Cancelled.")
        return
    
    # Create output directory
    OUTPUT_DIR.parent.mkdir(parents=True, exist_ok=True)
    
    # Download using Kaggle CLI
    print("\n🔽 Starting download...")
    try:
        result = subprocess.run(
            ["kaggle", "datasets", "download", "-d", DATASET_NAME, "-p", str(OUTPUT_DIR.parent)],
            capture_output=True,
            text=True,
            check=True
        )
        print(result.stdout)
        
        # Find the downloaded zip
        zip_path = OUTPUT_DIR.parent / "landscape-pictures.zip"
        if not zip_path.exists():
            zip_path = OUTPUT_DIR.parent / f"{DATASET_NAME.split('/')[-1]}.zip"
        
        if not zip_path.exists():
            print("❌ Downloaded zip file not found!")
            return
        
        print(f"\n📦 Download complete: {zip_path.name}")
        print("📂 Extracting images...")
        
        # Create temporary extraction directory
        temp_dir = OUTPUT_DIR.parent / "temp_extraction"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Extract all to temp first
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            members = zip_ref.namelist()
            total = len(members)
            
            print(f"Total files in dataset: {total:,}")
            print("Extracting all images first...\n")
            
            for i, member in enumerate(members, 1):
                zip_ref.extract(member, temp_dir)
                if i % 500 == 0 or i == total:
                    print(f"Extracted {i:,}/{total:,} files ({(i/total)*100:.1f}%)")
        
        print("\n📊 Selecting 3000 random images...")
        
        # Find all image files
        extensions = [".jpg", ".jpeg", ".png", ".JPG", ".JPEG", ".PNG"]
        all_images = []
        for ext in extensions:
            all_images.extend(list(temp_dir.rglob(f"*{ext}")))
        
        print(f"Found {len(all_images):,} total images")
        
        # Select random subset
        if len(all_images) > TARGET_IMAGE_COUNT:
            selected_images = random.sample(all_images, TARGET_IMAGE_COUNT)
            print(f"Randomly selected {TARGET_IMAGE_COUNT:,} images")
        else:
            selected_images = all_images
            print(f"Using all {len(all_images):,} images")
        
        # Move selected images to final directory
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        
        print("\n📁 Moving selected images to final location...")
        for i, img_path in enumerate(selected_images, 1):
            dest_path = OUTPUT_DIR / f"image_{i:05d}{img_path.suffix}"
            shutil.copy2(img_path, dest_path)
            
            if i % 500 == 0 or i == len(selected_images):
                print(f"Moved {i:,}/{len(selected_images):,} images ({(i/len(selected_images))*100:.1f}%)")
        
        # Clean up
        print("\n🗑️  Cleaning up temporary files...")
        shutil.rmtree(temp_dir)
        zip_path.unlink()
        
        # Count final images
        final_count = len(list(OUTPUT_DIR.glob("image_*.*")))
        
        print("\n✅ Dataset preparation complete!")
        print(f"\n📊 Final Image Summary:")
        print(f"   Total images: {final_count:,}")
        print(f"   📍 Location: {OUTPUT_DIR}")
        print(f"\n🎉 Ready for training with {final_count:,} diverse landscape images!")
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error downloading dataset: {e}")
        print(f"Output: {e.stdout}")
        print(f"Error: {e.stderr}")
        print("\nMake sure you accepted the dataset's terms on Kaggle website:")
        print("https://www.kaggle.com/datasets/arnaud58/landscape-pictures")

if __name__ == "__main__":
    print("\n🖼️  Kaggle Image Dataset Downloader for SoundCanvas")
    print("\nChoose an option:")
    print("1. Show Kaggle API setup instructions")
    print("2. Download dataset using Kaggle API (automated)")
    
    choice = input("\nEnter choice (1 or 2): ").strip()
    
    if choice == "1":
        setup_kaggle_instructions()
    elif choice == "2":
        download_kaggle_dataset()
    else:
        print("\n❌ Invalid choice. Please run again and choose 1 or 2.")