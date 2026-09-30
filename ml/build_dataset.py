"""Step 1 of training: turns every labeled photo into its 8 features and writes them to dataset.csv
with a stratified 80/20 train/test split. train.py and evaluate.ipynb read that file."""
import csv

from sklearn.model_selection import train_test_split

from data_files import DATASET_PATH, IMAGES_DIR, SEED, load_labels
from features import FEATURE_NAMES, compute_features

TEST_SHARE = 0.20


def assign_splits(labels: dict[str, str]) -> dict[str, str]:
    # Stratified so both halves have the same mix of genres. Sorted so the same seed always gives
    # the same split.
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
