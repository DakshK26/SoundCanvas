"""
Step 2 of training: fit the genre classifier, in two stages.

Stage 1 (rule labels): a small neural network, 8 image features in, two hidden
layers, 5 genre probabilities out, trained on the 1,890 rule-labeled images.
A few sizes and learning rates are tried and the one with the best validation
accuracy wins. The test splits are never looked at here (that is evaluate.py).
Saved as models/genre_classifier_rules.keras.

Stage 2 (human labels): the stage-1 model keeps training on 120 of our
hand-labeled images at a lower learning rate, so it moves toward human taste
without forgetting what it learned from 1,890 rule-labeled images. The other
30 decide when to stop. This is the model the ml service serves:
models/genre_classifier.keras. (Without human labels, stage 1 is served.)
"""
from itertools import product
from pathlib import Path

import numpy as np
import tensorflow as tf

from labeler import GENRES

DATASET_PATH = Path(__file__).parent / "data" / "dataset.npz"
MODELS_DIR = Path(__file__).parent / "models"
RULES_MODEL_PATH = MODELS_DIR / "genre_classifier_rules.keras"
SERVED_MODEL_PATH = MODELS_DIR / "genre_classifier.keras"
SEED = 42

# Stage 1 search. Small on purpose: 6 runs of a few seconds each, and a
# bigger search would start fitting the 270 validation images themselves.
HIDDEN_UNITS_OPTIONS = (32, 64, 128)
LEARNING_RATE_OPTIONS = (0.001, 0.01)
MAX_EPOCHS = 600
BATCH_SIZE = 32
PATIENCE = 40  # stop after this many epochs without a better validation accuracy

# Stage 2. Lower than any stage-1 rate: nudge the model toward our labels, don't retrain it.
FINE_TUNE_LEARNING_RATE = 0.0005
FINE_TUNE_HOLDOUT = 30  # of the 150 fine-tune images, used only to decide when to stop
FINE_TUNE_PATIENCE = 10


def class_weights(labels: np.ndarray) -> dict[int, float]:
    """Weights each genre by how rare it is, so the model does not just favor
    the common genres. A genre with half the average count gets weight 2."""
    counts = np.bincount(labels, minlength=len(GENRES))
    return {i: len(labels) / (len(GENRES) * c) for i, c in enumerate(counts) if c > 0}


def build_model(train_features: np.ndarray, hidden_units: int, learning_rate: float) -> tf.keras.Model:
    """Create the classifier: 8 features -> 2 hidden layers -> 5 genres."""
    # Rescales every feature to mean 0 and spread 1, using the training data.
    # Contrast only reaches 0.5 while colorfulness spans 0 to 1, so without
    # this the model would treat them unequally.
    normalize = tf.keras.layers.Normalization()
    normalize.adapt(train_features)

    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(8,)),
        normalize,
        tf.keras.layers.Dense(hidden_units, activation="relu"),
        tf.keras.layers.Dense(hidden_units, activation="relu"),
        tf.keras.layers.Dense(len(GENRES), activation="softmax"),
    ])
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
    """Stage 1: try each setting, keep the model with the best validation accuracy."""
    weights = class_weights(data["y_train"])
    print("class weights:", {GENRES[i]: round(float(w), 2) for i, w in weights.items()})

    best_model, best_accuracy = None, -1.0
    for hidden_units, learning_rate in product(HIDDEN_UNITS_OPTIONS, LEARNING_RATE_OPTIONS):
        tf.keras.utils.set_random_seed(SEED)
        model = build_model(data["x_train"], hidden_units, learning_rate)
        history = model.fit(
            data["x_train"], data["y_train"],
            validation_data=(data["x_val"], data["y_val"]),
            class_weight=weights,
            epochs=MAX_EPOCHS,
            batch_size=BATCH_SIZE,
            callbacks=[early_stopping(PATIENCE)],
            verbose=0,
        )
        _, accuracy = model.evaluate(data["x_val"], data["y_val"], verbose=0)
        print(f"  hidden={hidden_units:3d} lr={learning_rate}: validation {accuracy:.1%} "
              f"({len(history.history['loss'])} epochs)")
        if accuracy > best_accuracy:
            best_model, best_accuracy = model, accuracy

    print(f"stage 1 best validation accuracy: {best_accuracy:.1%}")
    return best_model


def fine_tune_on_humans(model: tf.keras.Model, data) -> tf.keras.Model:
    """Stage 2: keep training on hand-labeled images, stopping on a small held-back slice."""
    order = np.random.default_rng(SEED).permutation(len(data["y_tune"]))
    stop_idx, fit_idx = order[:FINE_TUNE_HOLDOUT], order[FINE_TUNE_HOLDOUT:]
    x_fit, y_fit = data["x_tune"][fit_idx], data["y_tune"][fit_idx]
    x_stop, y_stop = data["x_tune"][stop_idx], data["y_tune"][stop_idx]

    _, before = model.evaluate(x_stop, y_stop, verbose=0)
    tf.keras.utils.set_random_seed(SEED)
    compile_model(model, FINE_TUNE_LEARNING_RATE)  # the Normalization layer keeps its stage-1 statistics
    model.fit(
        x_fit, y_fit,
        validation_data=(x_stop, y_stop),
        class_weight=class_weights(y_fit),
        epochs=MAX_EPOCHS,
        batch_size=BATCH_SIZE,
        callbacks=[early_stopping(FINE_TUNE_PATIENCE)],
        verbose=0,
    )
    _, after = model.evaluate(x_stop, y_stop, verbose=0)
    print(f"stage 2 on the {FINE_TUNE_HOLDOUT} held-back human images: {before:.1%} -> {after:.1%}")
    return model


def main():
    data = np.load(DATASET_PATH)
    MODELS_DIR.mkdir(exist_ok=True)

    model = train_on_rules(data)
    model.save(RULES_MODEL_PATH)
    print(f"saved {RULES_MODEL_PATH}")

    if "y_tune" in data:
        model = fine_tune_on_humans(model, data)
    else:
        print("no human labels in the dataset, so the stage-1 model is served")
    model.save(SERVED_MODEL_PATH)
    print(f"saved {SERVED_MODEL_PATH}")


if __name__ == "__main__":
    main()
