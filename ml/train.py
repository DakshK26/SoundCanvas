"""
Step 2 of training: fit the genre classifier.

A small neural network: 8 image features in, two hidden layers, 5 genre
probabilities out. These settings were chosen by looking only at the
validation split. The test split is saved for evaluate.py.
"""
from pathlib import Path

import numpy as np
import tensorflow as tf

from labeler import GENRES

DATASET_PATH = Path(__file__).parent / "data" / "dataset.npz"
MODEL_PATH = Path(__file__).parent / "models" / "genre_classifier.keras"

HIDDEN_UNITS = 64
EPOCHS = 100
BATCH_SIZE = 32
LEARNING_RATE = 0.01
SEED = 42


def build_model(train_features: np.ndarray) -> tf.keras.Model:
    """Create the classifier: 8 features -> 2 hidden layers -> 5 genres."""
    # Rescales every feature to mean 0 and spread 1, using the training data.
    # Contrast only reaches 0.5 while colorfulness spans 0 to 1, so without
    # this the model would treat them unequally.
    normalize = tf.keras.layers.Normalization()
    normalize.adapt(train_features)

    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(8,)),
        normalize,
        tf.keras.layers.Dense(HIDDEN_UNITS, activation="relu"),
        tf.keras.layers.Dense(HIDDEN_UNITS, activation="relu"),
        tf.keras.layers.Dense(len(GENRES), activation="softmax"),
    ])
    model.compile(
        optimizer=tf.keras.optimizers.Adam(LEARNING_RATE),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model


def main():
    """Train on the train split, report validation accuracy, save the model."""
    tf.keras.utils.set_random_seed(SEED)
    data = np.load(DATASET_PATH)

    model = build_model(data["x_train"])
    model.fit(
        data["x_train"], data["y_train"],
        validation_data=(data["x_val"], data["y_val"]),
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        verbose=2,
    )

    _, val_accuracy = model.evaluate(data["x_val"], data["y_val"], verbose=0)
    print(f"Validation accuracy: {val_accuracy:.1%}")

    MODEL_PATH.parent.mkdir(exist_ok=True)
    model.save(MODEL_PATH)
    print(f"Saved model to {MODEL_PATH}")


if __name__ == "__main__":
    main()
