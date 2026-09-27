"""
Step 2 of training: choose the network size, fit it, and save it for the ml service.

A small neural network: 8 image features in, a few hidden layers, 5 genre
probabilities out. Only the 2,400 training photos are used; the test split is
scored once, in evaluate.ipynb.

  1. Model selection by 5-fold stratified cross-validation. Each candidate size is
     trained 5 times, each time holding out a different fifth of the training
     photos, and scored on the held-out fifth. Every photo is scored once, so the
     choice rests on 2,400 predictions rather than a single small validation set.
     Early stopping inside each fold also records how many epochs the size needs.
  2. The winner is retrained on all 2,400 photos for the average of those epoch
     counts, and saved to models/genre_classifier.keras.

Class weights (RETROWAVE is only 1.6% of the photos) were tried with the same
cross-validation and left out: accuracy fell from 79.0% to 74.5% to find 9 of the
37 RETROWAVE training photos instead of 1. Users can pick Retrowave themselves.
"""
from itertools import product

import numpy as np
import tensorflow as tf
from sklearn.model_selection import StratifiedKFold

from data_files import MODEL_PATH, SEED, load_split
from genres import GENRES

# Small on purpose: 4 candidates, so the search itself cannot overfit the folds.
HIDDEN_UNITS_OPTIONS = (64, 128)
HIDDEN_LAYERS_OPTIONS = (2, 3)
FOLDS = 5
LEARNING_RATE = 0.001  # Adam's default
MAX_EPOCHS = 300
BATCH_SIZE = 64
PATIENCE = 20  # stop after this many epochs without a better held-out accuracy


def build_model(train_features: np.ndarray, hidden_units: int, hidden_layers: int) -> tf.keras.Model:
    """8 features -> hidden layers -> 5 genre probabilities."""
    # Rescales every feature to mean 0 and spread 1, using the training data only.
    # Contrast only reaches 0.5 while colorfulness spans 0 to 1, so without
    # this the model would treat them unequally.
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
    """Held-out accuracy and best epoch count for each of the 5 folds."""
    # Accuracy, not loss: it is what we select on, and loss can rise from
    # overconfidence while the model's first choices are still getting better.
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

    results = {}
    for hidden_units, hidden_layers in product(HIDDEN_UNITS_OPTIONS, HIDDEN_LAYERS_OPTIONS):
        accuracies, epochs = cross_validate(x_train, y_train, hidden_units, hidden_layers)
        results[(hidden_units, hidden_layers)] = (np.mean(accuracies), round(np.mean(epochs)))
        print(f"  {hidden_layers} x {hidden_units:3d} units: {FOLDS}-fold accuracy "
              f"{np.mean(accuracies):.1%} +/- {np.std(accuracies):.1%} (about {round(np.mean(epochs))} epochs)")

    (hidden_units, hidden_layers), (accuracy, epochs) = max(results.items(), key=lambda item: item[1][0])
    print(f"chosen: {hidden_layers} x {hidden_units} units ({accuracy:.1%}); retraining on all "
          f"{len(y_train)} training photos for {epochs} epochs")

    tf.keras.utils.set_random_seed(SEED)
    model = build_model(x_train, hidden_units, hidden_layers)
    model.fit(x_train, y_train, epochs=epochs, batch_size=BATCH_SIZE, verbose=0)
    MODEL_PATH.parent.mkdir(exist_ok=True)
    model.save(MODEL_PATH)
    print(f"saved {MODEL_PATH}")


if __name__ == "__main__":
    main()
