from __future__ import annotations
from pathlib import Path
import numpy as np
import tensorflow as tf

DATA_PATH = Path("data/dataset.npz")
MODEL_EXPORT_PATH = Path("models/exported_model")

def load_dataset():
    data = np.load(DATA_PATH)
    X = data["X"].astype("float32")
    Y = data["Y"].astype("float32")
    return X, Y

def build_model(input_dim: int, output_dim: int) -> tf.keras.Model:
    inputs = tf.keras.Input(shape=(input_dim,))
    x = tf.keras.layers.Dense(32, activation="relu")(inputs)
    x = tf.keras.layers.Dense(32, activation="relu")(x)
    outputs = tf.keras.layers.Dense(output_dim, activation="linear")(x)
    
    model = tf.keras.Model(inputs, outputs)
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3),
        loss="mse",
        metrics=["mae"],
    )
    return model

def main():
    X, Y = load_dataset()
    n_samples, input_dim = X.shape
    _, output_dim = Y.shape
    
    print(f"Dataset shape: X={X.shape}, Y={Y.shape}")

    model = build_model(input_dim, output_dim)
    
    print("\nModel architecture:")
    model.summary()

    print("\nTraining...")
    model.fit(
        X,
        Y,
        batch_size=16,
        epochs=20,
        validation_split=0.2,
        verbose=1,
    )

    MODEL_EXPORT_PATH.mkdir(parents=True, exist_ok=True)
    model.export(MODEL_EXPORT_PATH)  # Use export() for TensorFlow Serving
    
    print(f"\nModel exported to {MODEL_EXPORT_PATH}")

if __name__ == "__main__":
    main()