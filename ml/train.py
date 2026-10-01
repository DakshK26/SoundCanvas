"""Step 2 of training, run by hand after build_dataset.py. It reads the train rows of
ml/data/dataset.csv, picks the network size with 5-fold cross-validation, retrains that size on the
whole training split and saves ml/models/genre_classifier.keras, which app.py loads. The test rows
are never touched here; evaluate.ipynb scores the saved model on them."""
from itertools import product

import numpy as np
import tensorflow as tf
from sklearn.model_selection import StratifiedKFold

from dataset import MODEL_PATH, SEED, load_split
from genres import GENRES

# The four candidate sizes are every pairing of these: 2 or 3 hidden layers of 64 or 128 units.
HIDDEN_UNITS_OPTIONS = (64, 128)
HIDDEN_LAYERS_OPTIONS = (2, 3)
FOLDS = 5
LEARNING_RATE = 0.001
MAX_EPOCHS = 300  # an upper limit only; early stopping normally ends each fold well before this
BATCH_SIZE = 64
PATIENCE = 20  # epochs


def build_model(train_features: np.ndarray, hidden_units: int, hidden_layers: int) -> tf.keras.Model:
    # The features have different ranges (contrast stays under 0.5, the others use 0..1), so the
    # first layer rescales each one to mean 0 and standard deviation 1. adapt() measures those
    # means and deviations from the training rows only, so nothing about held-out rows leaks in.
    # Normalization is part of the saved model, so app.py sends raw features.
    normalize = tf.keras.layers.Normalization()
    normalize.adapt(train_features)

    # 8 inputs, then the hidden layers. Each is fully connected with ReLU (negative values become
    # 0), which lets the network learn non-linear boundaries between genres.
    # The output layer has one unit per genre. Softmax turns them into probabilities that sum to 1,
    # in the same order as GENRES.
    model = tf.keras.Sequential(
        [tf.keras.layers.Input(shape=(8,)), normalize]
        + [tf.keras.layers.Dense(hidden_units, activation="relu") for _ in range(hidden_layers)]
        + [tf.keras.layers.Dense(len(GENRES), activation="softmax")]
    )
    # Adam is a gradient descent optimiser that adapts the step size for each weight.
    # Cross-entropy penalises giving a low probability to the true genre. The "sparse" version takes
    # the label as a plain genre index (0 to 3), which is what load_split returns, so the labels
    # don't need converting to one-hot vectors first.
    model.compile(
        optimizer=tf.keras.optimizers.Adam(LEARNING_RATE),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model


def cross_validate(x: np.ndarray, y: np.ndarray, hidden_units: int, hidden_layers: int) -> tuple[list[float], list[int]]:
    """Best held-out accuracy and the epoch it came at, per fold."""
    # Each fold stops once held-out accuracy hasn't improved for PATIENCE epochs. It watches
    # accuracy because accuracy is the number the size is chosen on. Stopping there avoids
    # overfitting (the network memorising its training rows and getting worse on new ones).
    # restore_best_weights rolls the model back to its best epoch.
    early_stopping = tf.keras.callbacks.EarlyStopping(
        monitor="val_accuracy", mode="max", patience=PATIENCE, restore_best_weights=True)
    # Stratified folds keep the genre mix of every fold the same as the whole training split, so no
    # fold is scored on an unusual share of one genre. The fixed seed makes the folds repeatable.
    folds = StratifiedKFold(n_splits=FOLDS, shuffle=True, random_state=SEED)

    accuracies, epochs = [], []
    # folds.split gives row numbers, not rows: about 4/5 of the training split to fit on and the
    # other 1/5 to score on. Every row is held out exactly once across the 5 folds.
    for fit_rows, held_out in folds.split(x, y):
        # A fresh model per fold, with the same seed, so every fold starts from the same random
        # weights and the folds differ only in their data. Its normalisation is fitted on this
        # fold's fit rows only.
        tf.keras.utils.set_random_seed(SEED)
        model = build_model(x[fit_rows], hidden_units, hidden_layers)
        history = model.fit(x[fit_rows], y[fit_rows], validation_data=(x[held_out], y[held_out]),
                            epochs=MAX_EPOCHS, batch_size=BATCH_SIZE, callbacks=[early_stopping], verbose=0)
        # history holds the held-out accuracy after every epoch, including the PATIENCE epochs after
        # the best one. Record the best accuracy and the epoch it happened at (argmax counts from 0,
        # epochs count from 1).
        held_out_accuracy = history.history["val_accuracy"]
        accuracies.append(max(held_out_accuracy))
        epochs.append(int(np.argmax(held_out_accuracy)) + 1)
    return accuracies, epochs


def main():
    # Only the train rows of dataset.csv. The test rows stay unseen until evaluate.ipynb.
    x_train, y_train = load_split("train")

    # Try all four sizes and keep the one with the best average held-out accuracy.
    # product gives every pairing of units and layers. For each size this stores the mean accuracy
    # over the 5 folds and the average best epoch, rounded to a whole number.
    results = {}
    for hidden_units, hidden_layers in product(HIDDEN_UNITS_OPTIONS, HIDDEN_LAYERS_OPTIONS):
        accuracies, epochs = cross_validate(x_train, y_train, hidden_units, hidden_layers)
        results[(hidden_units, hidden_layers)] = (np.mean(accuracies), round(np.mean(epochs)))
        print(f"  {hidden_layers} x {hidden_units:3d} units: {FOLDS}-fold accuracy "
              f"{np.mean(accuracies):.1%} +/- {np.std(accuracies):.1%} (about {round(np.mean(epochs))} epochs)")

    # The key picks the entry with the highest mean accuracy (item[1][0]), and the line unpacks
    # that entry into the chosen size and its epoch count.
    (hidden_units, hidden_layers), (accuracy, epochs) = max(results.items(), key=lambda item: item[1][0])
    print(f"chosen: {hidden_layers} x {hidden_units} units ({accuracy:.1%}); retraining on all "
          f"{len(y_train)} training photos for {epochs} epochs")

    # Retrain the chosen size on every training row, so the final model learns from more data than
    # any single fold did.
    # No held-out rows are left to stop on, so train for the folds' average best epoch count.
    tf.keras.utils.set_random_seed(SEED)
    model = build_model(x_train, hidden_units, hidden_layers)
    model.fit(x_train, y_train, epochs=epochs, batch_size=BATCH_SIZE, verbose=0)
    # MODEL_PATH is the same path app.py loads at start-up and evaluate.ipynb scores.
    MODEL_PATH.parent.mkdir(exist_ok=True)
    model.save(MODEL_PATH)
    print(f"saved {MODEL_PATH}")


if __name__ == "__main__":
    main()
