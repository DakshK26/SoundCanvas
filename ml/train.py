"""
Step 2 of training: fit the genre classifier and save it for the ml service.

A small neural network: 8 image features in, a few hidden layers, 5 genre
probabilities out. A handful of network sizes are tried, and the one with the
best validation accuracy is saved to models/genre_classifier.keras. The test
split is never touched here; evaluate.ipynb scores it once.

Two common fixes were tried on the validation split and left out:
  - Class weights, since RETROWAVE is only 1.6% of the photos. They cost about
    4 points of accuracy (76% -> 72%) to catch 1 of the 5 validation RETROWAVE photos.
  - Training on jittered copies of each photo. Accuracy stayed the same, so it
    is not worth the extra code.
"""
from itertools import product

import tensorflow as tf

from data_files import MODEL_PATH, SEED, load_split
from genres import GENRES

# Small on purpose: 4 runs. A bigger search would start fitting the 300
# validation images themselves.
HIDDEN_UNITS_OPTIONS = (64, 128)
HIDDEN_LAYERS_OPTIONS = (2, 3)
LEARNING_RATE = 0.001  # Adam's default
MAX_EPOCHS = 300
BATCH_SIZE = 64
PATIENCE = 20  # stop after this many epochs without a better validation accuracy


def build_model(train_features, hidden_units: int, hidden_layers: int) -> tf.keras.Model:
    """8 features -> hidden layers -> 5 genre probabilities."""
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
    model.compile(
        optimizer=tf.keras.optimizers.Adam(LEARNING_RATE),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model


def main():
    x_train, y_train = load_split("train")
    x_val, y_val = load_split("validation")

    # Stops when validation accuracy stops improving and keeps the best epoch's weights.
    # Accuracy, not loss: it is what we select on, and loss can rise from
    # overconfidence while the model's first choices are still getting better.
    early_stopping = tf.keras.callbacks.EarlyStopping(
        monitor="val_accuracy", mode="max", patience=PATIENCE, restore_best_weights=True)

    best_model, best_accuracy = None, -1.0
    for hidden_units, hidden_layers in product(HIDDEN_UNITS_OPTIONS, HIDDEN_LAYERS_OPTIONS):
        tf.keras.utils.set_random_seed(SEED)
        model = build_model(x_train, hidden_units, hidden_layers)
        history = model.fit(x_train, y_train, validation_data=(x_val, y_val), epochs=MAX_EPOCHS,
                            batch_size=BATCH_SIZE, callbacks=[early_stopping], verbose=0)
        _, accuracy = model.evaluate(x_val, y_val, verbose=0)
        print(f"  {hidden_layers} x {hidden_units:3d} units: validation {accuracy:.1%} "
              f"({len(history.history['loss'])} epochs)")
        if accuracy > best_accuracy:
            best_model, best_accuracy = model, accuracy

    MODEL_PATH.parent.mkdir(exist_ok=True)
    best_model.save(MODEL_PATH)
    print(f"best validation accuracy {best_accuracy:.1%}; saved {MODEL_PATH}")


if __name__ == "__main__":
    main()
