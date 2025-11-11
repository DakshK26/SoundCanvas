"""
TensorFlow model server compatible with TF Serving REST API.
Designed for Apple Silicon compatibility.
"""
from pathlib import Path
import numpy as np
import tensorflow as tf
from flask import Flask, request, jsonify

# Model path - when running in Docker, models are in /app/models
MODEL_PATH = Path("/app/models/exported_model_versioned/1")

# Load model at startup using TFSMLayer for Keras 3 compatibility
print(f"Loading model from {MODEL_PATH}...")
loaded_model = tf.keras.layers.TFSMLayer(str(MODEL_PATH), call_endpoint='serving_default')
print("Model loaded successfully!")

app = Flask(__name__)

@app.route('/v1/models/soundcanvas:predict', methods=['POST'])
def predict():
    """TF Serving compatible prediction endpoint."""
    try:
        data = request.get_json()
        instances = np.array(data['instances'], dtype='float32')
        
        # Call the loaded model
        predictions = loaded_model(instances)
        
        # Extract the output tensor and convert to numpy
        if isinstance(predictions, dict):
            # If model returns a dict, get the first output
            predictions = list(predictions.values())[0]
        
        return jsonify({'predictions': predictions.numpy().tolist()})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/v1/models/soundcanvas', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'model_version_status': [{
            'version': '1',
            'state': 'AVAILABLE'
        }]
    })

if __name__ == '__main__':
    print("="*50)
    print("TensorFlow Model Server")
    print("Listening on http://0.0.0.0:8501")
    print("="*50)
    app.run(host='0.0.0.0', port=8501, debug=False)