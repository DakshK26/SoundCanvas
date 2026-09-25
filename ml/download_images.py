"""
Step 0 of training: fetch the raw images.

Downloads the Flickr8k dataset from Kaggle (8,091 everyday Flickr photos:
people, pets, sports, concerts, beaches, snow, city nights) and copies a fixed
random sample of 3,000 into data/raw_images as image_00001.jpg ... image_03000.jpg.

Why Flickr8k: it looks like what people upload, with a wide spread of
brightness, color and mood. An earlier landscape-photo dataset was mostly
dramatic skies, so nearly every image felt "cinematic".

Needs Kaggle credentials: kaggle.json in ~/.kaggle or in KAGGLE_CONFIG_DIR.
Run:  python download_images.py
"""
import random
import shutil
import tempfile
import zipfile
from pathlib import Path

from data_files import IMAGES_DIR, SEED

KAGGLE_DATASET = "adityajn105/flickr8k"
IMAGE_COUNT = 3000  # enough for a 2,100 / 300 / 600 split; labeling all 8,091 adds little


def main():
    from kaggle.api.kaggle_api_extended import KaggleApi  # imported here so the other scripts don't need kaggle

    api = KaggleApi()
    api.authenticate()
    with tempfile.TemporaryDirectory() as tmp:
        print(f"downloading {KAGGLE_DATASET} (about 1 GB)...")
        api.dataset_download_files(KAGGLE_DATASET, path=tmp, quiet=False)
        with zipfile.ZipFile(next(Path(tmp).glob("*.zip"))) as archive:
            photos = sorted(name for name in archive.namelist() if name.lower().endswith(".jpg"))
            chosen = random.Random(SEED).sample(photos, IMAGE_COUNT)

            if IMAGES_DIR.exists():
                shutil.rmtree(IMAGES_DIR)
            IMAGES_DIR.mkdir(parents=True)
            for number, name in enumerate(chosen, start=1):
                (IMAGES_DIR / f"image_{number:05d}.jpg").write_bytes(archive.read(name))

    print(f"saved {IMAGE_COUNT} of {len(photos)} photos to {IMAGES_DIR}")


if __name__ == "__main__":
    main()
