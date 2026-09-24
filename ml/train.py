"""
Step 2 of training: fit the genre classifier, in two stages.

Stage 1 (rule labels): a small neural network, 8 image features in, a few
hidden layers, 5 genre probabilities out, trained on the 1,889 rule-labeled
images plus nudged copies of them (see augment). A few network sizes are tried
and the one with the best validation accuracy wins. The test splits are never
looked at here (that is evaluate.py). This is the model the ml service serves:
models/genre_classifier.keras.

Stage 2 (human labels, an experiment): the stage-1 model keeps training on 210
of the 300 labeled-by-eye images at a lower learning rate. The 30 human
validation images decide when to stop. Saved as models/genre_classifier_human.keras
and scored by evaluate.py, but not served: it matches our eye better, and
matches the rules worse.
"""
from itertools import product
from pathlib import Path

import numpy as np
import tensorflow as tf

from labeler import GENRES, label_genre

DATASET_PATH = Path(__file__).parent / "data" / "dataset.npz"
MODELS_DIR = Path(__file__).parent / "models"
SERVED_MODEL_PATH = MODELS_DIR / "genre_classifier.keras"
HUMAN_MODEL_PATH = MODELS_DIR / "genre_classifier_human.keras"
SEED = 42

# Stage 1 search. Small on purpose: 4 runs, and a bigger search would start
# fitting the 270 validation images themselves.
HIDDEN_UNITS_OPTIONS = (64, 128)
HIDDEN_LAYERS_OPTIONS = (2, 3)
LEARNING_RATE = 0.001
MAX_EPOCHS = 300
BATCH_SIZE = 128
PATIENCE = 20  # stop after this many epochs without a better validation accuracy

# Augmentation: 10 nudged copies of each training image, each feature moved by
# about 5% of its spread. Only the training split is augmented.
AUGMENT_COPIES = 10
AUGMENT_NOISE = 0.05

# Stage 2. Lower than the stage-1 rate: nudge the model toward our labels, don't retrain it.
FINE_TUNE_LEARNING_RATE = 0.0005
FINE_TUNE_BATCH_SIZE = 32
FINE_TUNE_PATIENCE = 10


def class_weights(labels: np.ndarray) -> dict[int, float]:
    """Weights each genre by how rare it is, so the model does not just favor
    the common genres. A genre with half the average count gets weight 2."""
    counts = np.bincount(labels, minlength=len(GENRES))
    return {i: len(labels) / (len(GENRES) * c) for i, c in enumerate(counts) if c > 0}


def augment(features: np.ndarray, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    """Adds nudged copies of each training image and labels them with the same rules.

    The rules draw sharp lines (brightness 0.30, energy 0.55, ...), and with only
    1,889 real images few of them sit near those lines, so the network guesses
    where the lines are. Because the labels come from a known function, we can
    make extra points close to real ones and label them exactly. This teaches
    the boundaries without making any test image easier or harder.
    """
    spread = features.std(axis=0)
    copies = [features] + [
        np.clip(features + rng.normal(0.0, AUGMENT_NOISE, features.shape) * spread, 0.0, 1.0)
        for _ in range(AUGMENT_COPIES)
    ]
    x = np.concatenate(copies)
    y = np.array([GENRES.index(label_genre(row)) for row in x])
    return x, y


def build_model(train_features: np.ndarray, hidden_units: int, hidden_layers: int,
                learning_rate: float) -> tf.keras.Model:
    """Create the classifier: 8 features -> hidden layers -> 5 genres."""
    # Rescales every feature to mean 0 and spread 1, using the training data.
    # Contrast only reaches 0.5 while colorfulness spans 0 to 1, so without
    # this the model would treat them unequally.
    normalize = tf.keras.layers.Normalization()
    normalize.adapt(train_features)

    model = tf.keras.Sequential(
        [tf.keras.layers.Input(shape=(8,)), normalize]
        + [tf.keras.layers.Dense(hidden_units, activation="relu") for _ in range(hidden_layers)]
        + [tf.keras.layers.Dense(len(GENRES), activation="softmax")]
    )
    compile_model(model, learning_rate)
    return model


def compile_model(model: tf.keras.Model, learning_rate: float) -> None:
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )


def early_stopping(patience: int) -> tf.keras.callbacks.EarlyStopping:
    """Stops when validation accuracy stops improving and keeps the best epoch's weights.
    Accuracy, not loss: it is what we select on, and loss can rise from overconfidence
    while the model's first choices are still getting better."""
    return tf.keras.callbacks.EarlyStopping(monitor="val_accuracy", mode="max", patience=patience,
                                            restore_best_weights=True)


def train_on_rules(data) -> tf.keras.Model:
    """Stage 1: try each setting, keep the model with the best validation accuracy.

    No class weights here: every genre has at least 11% of the images, and
    weighting rare genres up trades overall accuracy for them. evaluate.py
    prints per-genre accuracy so a neglected genre would still show."""
    x_train, y_train = augment(data["x_train"], np.random.default_rng(SEED))
    print(f"training on {len(y_train)} images ({len(data['y_train'])} real + nudged copies)")

    best_model, best_accuracy = None, -1.0
    for hidden_units, hidden_layers in product(HIDDEN_UNITS_OPTIONS, HIDDEN_LAYERS_OPTIONS):
        tf.keras.utils.set_random_seed(SEED)
        model = build_model(x_train, hidden_units, hidden_layers, LEARNING_RATE)
        history = model.fit(
            x_train, y_train,
            validation_data=(data["x_val"], data["y_val"]),
            epochs=MAX_EPOCHS,
            batch_size=BATCH_SIZE,
            callbacks=[early_stopping(PATIENCE)],
            verbose=0,
        )
        _, accuracy = model.evaluate(data["x_val"], data["y_val"], verbose=0)
        print(f"  {hidden_layers} x {hidden_units:3d} units: validation {accuracy:.1%} "
              f"({len(history.history['loss'])} epochs)")
        if accuracy > best_accuracy:
            best_model, best_accuracy = model, accuracy

    print(f"stage 1 best validation accuracy: {best_accuracy:.1%}")
    return best_model


def fine_tune_on_humans(model: tf.keras.Model, data) -> tf.keras.Model:
    """Stage 2: keep training on hand-labeled images, stopping on the human validation split."""
    x_fit, y_fit = data["x_tune"], data["y_tune"]
    x_stop, y_stop = data["x_human_val"], data["y_human_val"]

    _, before = model.evaluate(x_stop, y_stop, verbose=0)
    tf.keras.utils.set_random_seed(SEED)
    compile_model(model, FINE_TUNE_LEARNING_RATE)  # the Normalization layer keeps its stage-1 statistics
    model.fit(
        x_fit, y_fit,
        validation_data=(x_stop, y_stop),
        class_weight=class_weights(y_fit),
        epochs=MAX_EPOCHS,
        batch_size=FINE_TUNE_BATCH_SIZE,
        callbacks=[early_stopping(FINE_TUNE_PATIENCE)],
        verbose=0,
    )
    _, after = model.evaluate(x_stop, y_stop, verbose=0)
    print(f"stage 2 on the {len(y_stop)} human validation images: {before:.1%} -> {after:.1%}")
    return model


def main():
    data = np.load(DATASET_PATH)
    MODELS_DIR.mkdir(exist_ok=True)

    model = train_on_rules(data)
    model.save(SERVED_MODEL_PATH)
    print(f"saved {SERVED_MODEL_PATH}")

    if "y_tune" in data:
        model = fine_tune_on_humans(model, data)
        model.save(HUMAN_MODEL_PATH)
        print(f"saved {HUMAN_MODEL_PATH}")
    else:
        print("no human labels in the dataset, so stage 2 is skipped")


if __name__ == "__main__":
    main()
