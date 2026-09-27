"""
Step 1 of training: turn data/labels.csv into data/dataset.csv.

Computes each labeled photo's 8 features (features.py) and assigns it a split:
  train  80%  used by train.py, which cross-validates on it to choose the network
  test   20%  scored once, in evaluate.ipynb, and never used to make a choice
The split is stratified: each genre is divided 80/20 on its own, so a rare
genre cannot end up missing from the test set by chance.
"""
import csv

from sklearn.model_selection import train_test_split

from data_files import DATASET_PATH, IMAGES_DIR, SEED, load_labels
from features import FEATURE_NAMES, compute_features

TEST_SHARE = 0.20


def assign_splits(labels: dict[str, str]) -> dict[str, str]:
    """Image filename -> "train" or "test"."""
    images = sorted(labels)
    train, test = train_test_split(images, test_size=TEST_SHARE, random_state=SEED,
                                   stratify=[labels[image] for image in images])
    return {image: split for split, names in (("train", train), ("test", test)) for image in names}


def main():
    labels = load_labels()
    splits = assign_splits(labels)
    with DATASET_PATH.open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["image", "split", "genre", *FEATURE_NAMES])
        for image in sorted(labels):
            features = compute_features(IMAGES_DIR / image)
            writer.writerow([image, splits[image], labels[image], *(f"{value:.6f}" for value in features)])

    counts = {split: list(splits.values()).count(split) for split in ("train", "test")}
    print(f"saved {DATASET_PATH}: {len(labels)} images, " + ", ".join(f"{n} {s}" for s, n in counts.items()))


if __name__ == "__main__":
    main()
