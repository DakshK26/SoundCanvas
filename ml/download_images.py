"""
training step 0: get the photos.

pulls Flickr8k from kaggle (8,091 everyday photos - people, pets, sports, concerts,
beaches, snow, city at night) and copies a fixed random 3,000 into data/raw_images
as image_00001.jpg .. image_03000.jpg

why flickr8k: it looks like what people would actually upload, lots of variety in
brightness/colour/mood. the landscape dataset I used before was mostly dramatic skies
so basically everything came out "cinematic"

needs kaggle creds: kaggle.json in ~/.kaggle or KAGGLE_CONFIG_DIR (never commit it)
run:  python download_images.py
"""
import random
import shutil
import tempfile
import zipfile
from pathlib import Path

from data_files import IMAGES_DIR, SEED

KAGGLE_DATASET = "adityajn105/flickr8k"
IMAGE_COUNT = 3000  # -> 2,400 train / 600 test. all 8,091 wouldn't add much


def main():
    from kaggle.api.kaggle_api_extended import KaggleApi  # lazy import, nothing else needs the kaggle package

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
