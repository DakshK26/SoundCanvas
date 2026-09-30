"""Step 2 of training: picks the network size with 5-fold cross-validation on the training split,
then retrains it on the whole training split and saves it for app.py. The test split is left for
evaluate.ipynb."""
from itertools import product

import numpy as np
import tensorflow as tf
from sklearn.model_selection import StratifiedKFold

from data_files import MODEL_PATH, SEED, load_split
from genres import GENRES

HIDDEN_UNITS_OPTIONS = (64, 128)
HIDDEN_LAYERS_OPTIONS = (2, 3)
FOLDS = 5
LEARNING_RATE = 0.001
MAX_EPOCHS = 300
BATCH_SIZE = 64
PATIENCE = 20  # epochs


def build_model(train_features: np.ndarray, hidden_units: int, hidden_layers: int) -> tf.keras.Model:
    # Normalization is part of the saved model, so app.py sends raw features.
    normalize = tf.keras.layers.Normalization()
    normalize.adapt(train_features)

    model = tf.keras.Sequential(
        [tf.keras.layers.Input(shape=(8,)), normalize]
        + [tf.keras.layers.Dense(hidden_units, activation="relu") for _ in range(hidden_layers)]
        + [tf.keras.layers.Dense(len(GENRES), activation="softmax")]
    )
    model.compile(
        optimizer=tf.keras.optimizers.Adam(LEARNING_RATE),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model


def cross_validate(x: np.ndarray, y: np.ndarray, hidden_units: int, hidden_layers: int) -> tuple[list[float], list[int]]:
    """Best held-out accuracy and the epoch it came at, per fold."""
    # Each fold stops once held-out accuracy hasn't improved for PATIENCE epochs.
    early_stopping = tf.keras.callbacks.EarlyStopping(
        monitor="val_accuracy", mode="max", patience=PATIENCE, restore_best_weights=True)
    folds = StratifiedKFold(n_splits=FOLDS, shuffle=True, random_state=SEED)

    accuracies, epochs = [], []
    for fit_rows, held_out in folds.split(x, y):
        tf.keras.utils.set_random_seed(SEED)
        model = build_model(x[fit_rows], hidden_units, hidden_layers)
        history = model.fit(x[fit_rows], y[fit_rows], validation_data=(x[held_out], y[held_out]),
                            epochs=MAX_EPOCHS, batch_size=BATCH_SIZE, callbacks=[early_stopping], verbose=0)
        held_out_accuracy = history.history["val_accuracy"]
        accuracies.append(max(held_out_accuracy))
        epochs.append(int(np.argmax(held_out_accuracy)) + 1)
    return accuracies, epochs


def main():
    x_train, y_train = load_split("train")

    # Try all four sizes and keep the one with the best average held-out accuracy.
    results = {}
    for hidden_units, hidden_layers in product(HIDDEN_UNITS_OPTIONS, HIDDEN_LAYERS_OPTIONS):
        accuracies, epochs = cross_validate(x_train, y_train, hidden_units, hidden_layers)
        results[(hidden_units, hidden_layers)] = (np.mean(accuracies), round(np.mean(epochs)))
        print(f"  {hidden_layers} x {hidden_units:3d} units: {FOLDS}-fold accuracy "
              f"{np.mean(accuracies):.1%} +/- {np.std(accuracies):.1%} (about {round(np.mean(epochs))} epochs)")

    (hidden_units, hidden_layers), (accuracy, epochs) = max(results.items(), key=lambda item: item[1][0])
    print(f"chosen: {hidden_layers} x {hidden_units} units ({accuracy:.1%}); retraining on all "
          f"{len(y_train)} training photos for {epochs} epochs")

    # No held-out rows are left to stop on, so train for the folds' average best epoch count.
    tf.keras.utils.set_random_seed(SEED)
    model = build_model(x_train, hidden_units, hidden_layers)
    model.fit(x_train, y_train, epochs=epochs, batch_size=BATCH_SIZE, verbose=0)
    MODEL_PATH.parent.mkdir(exist_ok=True)
    model.save(MODEL_PATH)
    print(f"saved {MODEL_PATH}")


if __name__ == "__main__":
    main()
