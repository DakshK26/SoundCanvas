"""
Train a neural network to map image features → music parameters.
Phase 5.5 version with richer features and parameters.
"""
import numpy as np
import tensorflow as tf
from pathlib import Path

# Phase 5.5 dimensions (matching Person A's dataset)
INPUT_DIM = 8   # [avgR, avgG, avgB, brightness, hue, saturation, colorfulness, contrast]
OUTPUT_DIM = 7  # [tempo_bpm, base_freq, energy, brightness, reverb, scale_type, pattern_type]

def load_dataset(dataset_path):
    """Load the .npz dataset created by dataset.py."""
    data = np.load(dataset_path)
    
    # Person A used "X" and "Y" as keys, not "features" and "params"
    X = data["X"]  # shape: (N, INPUT_DIM)
    Y = data["Y"]  # shape: (N, OUTPUT_DIM)
    
    print(f"✅ Loaded dataset: X={X.shape}, Y={Y.shape}")
    print(f"\n📊 Feature ranges:")
    feature_names = ["avgR", "avgG", "avgB", "brightness", "hue", "saturation", "colorfulness", "contrast"]
    for i, name in enumerate(feature_names):
        print(f"  {name:15s}: [{X[:, i].min():.3f}, {X[:, i].max():.3f}]")
    
    print(f"\n📊 Parameter ranges:")
    param_names = ["tempo_bpm", "base_freq", "energy", "brightness", "reverb", "scale_type", "pattern_type"]
    for i, name in enumerate(param_names):
        print(f"  {name:15s}: [{Y[:, i].min():.3f}, {Y[:, i].max():.3f}]")
    
    return X, Y

def build_model(input_dim, output_dim):
    """Build a deeper network for richer feature mapping."""
    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(input_dim,)),
        tf.keras.layers.Dense(128, activation="relu", name="hidden1"),
        tf.keras.layers.BatchNormalization(),
        tf.keras.layers.Dropout(0.2),
        tf.keras.layers.Dense(128, activation="relu", name="hidden2"),
        tf.keras.layers.BatchNormalization(),
        tf.keras.layers.Dropout(0.2),
        tf.keras.layers.Dense(64, activation="relu", name="hidden3"),
        tf.keras.layers.Dense(output_dim, activation="linear", name="output"),
    ])
    
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
        loss="mse",
        metrics=["mae"]
    )
    
    return model

def train_model():
    """Train the model on the new dataset."""
    dataset_path = Path(__file__).parent.parent / "data" / "dataset.npz"
    
    if not dataset_path.exists():
        raise FileNotFoundError(
            f"Dataset not found at {dataset_path}.\n"
            "Run 'python -m src.dataset' first to generate the dataset."
        )
    
    print("\n🧠 Phase 5.5 Model Training")
    print("="*70)
    
    X, Y = load_dataset(dataset_path)
    
    # Train/validation split
    split_idx = int(0.8 * len(X))
    X_train, X_val = X[:split_idx], X[split_idx:]
    Y_train, Y_val = Y[:split_idx], Y[split_idx:]
    
    print(f"\n📚 Dataset split:")
    print(f"  Training:   {len(X_train):,} samples")
    print(f"  Validation: {len(X_val):,} samples")
    
    model = build_model(INPUT_DIM, OUTPUT_DIM)
    
    print(f"\n🏗️  Model architecture:")
    model.summary()
    
    print(f"\n🚀 Starting training...")
    print("="*70 + "\n")
    
    # Train
    history = model.fit(
        X_train, Y_train,
        validation_data=(X_val, Y_val),
        epochs=100,
        batch_size=32,
        callbacks=[
            tf.keras.callbacks.EarlyStopping(
                monitor='val_loss',
                patience=15,
                restore_best_weights=True,
                verbose=1
            ),
            tf.keras.callbacks.ReduceLROnPlateau(
                monitor='val_loss',
                factor=0.5,
                patience=5,
                verbose=1
            ),
        ],
        verbose=1,
    )
    
    # Save model
    export_dir = Path(__file__).parent.parent / "models" / "exported_model_versioned" / "1"
    export_dir.mkdir(parents=True, exist_ok=True)
    model.export(str(export_dir))
    
    print("\n" + "="*70)
    print("✅ Training complete!")
    print("="*70)
    print(f"\n📊 Final Results:")
    print(f"  Validation Loss (MSE): {history.history['val_loss'][-1]:.4f}")
    print(f"  Validation MAE:        {history.history['val_mae'][-1]:.4f}")
    print(f"\n💾 Model saved to: {export_dir}")
    print(f"\n🎯 Next steps:")
    print(f"  1. Test predictions: python -m src.test_inference_local")
    print(f"  2. Start TF serving: docker-compose up tf-serving")
    print("="*70 + "\n")

if __name__ == "__main__":
    train_model()