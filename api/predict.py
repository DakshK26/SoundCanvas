from http.server import BaseHTTPRequestHandler
import json
import os

# Mock ML logic to replace TensorFlow Serving for Vercel deployment
# This ensures the API works without the heavy TF dependency

def heuristic_predict(features):
    """
    Heuristic mapping from features to music parameters.
    Matches the logic in ml/src/pseudo_labels.py
    """
    # Features: [avgR, avgG, avgB, brightness, hue, saturation, colorfulness, contrast]
    brightness = features[3]
    hue = features[4]
    saturation = features[5]
    colorfulness = features[6]
    
    # 1. Tempo (40-90 BPM) - Brightness drives tempo
    tempo = 40 + (brightness * 50)
    
    # 2. Base Frequency (100-400 Hz) - Warm colors (Red) = higher freq? 
    # Actually, let's use R vs B.
    avg_r = features[0]
    avg_b = features[2]
    warmth = avg_r - avg_b # -1 to 1
    base_freq = 250 + (warmth * 150)
    
    # 3. Energy (0-1) - Saturation + Colorfulness
    energy = (saturation + colorfulness) / 2.0
    
    # 4. Brightness (Timbre) (0-1) - Brightness
    timbre_bright = brightness
    
    # 5. Reverb (0-1) - Inverse of brightness (Dark = more reverb)
    reverb = 1.0 - brightness
    
    # 6. Scale Type (0-3) - Hue based
    # 0=Major, 1=Minor, 2=Dorian, 3=Lydian
    if hue < 0.1 or hue > 0.9: # Red
        scale = 0 # Major
    elif hue < 0.4: # Green
        scale = 3 # Lydian
    elif hue < 0.7: # Blue
        scale = 1 # Minor
    else: # Purple
        scale = 2 # Dorian
        
    # 7. Pattern Type (0-2) - Energy based
    # 0=Pad, 1=Arp, 2=Chords
    if energy < 0.3:
        pattern = 0
    elif energy > 0.7:
        pattern = 1
    else:
        pattern = 2
        
    return [tempo, base_freq, energy, timbre_bright, reverb, float(scale), float(pattern)]

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            body = json.loads(post_data.decode('utf-8'))
            instances = body.get('instances', [])
            
            predictions = []
            for instance in instances:
                # instance is expected to be [8] floats
                if len(instance) == 8:
                    pred = heuristic_predict(instance)
                    predictions.append(pred)
                else:
                    predictions.append([0]*7) # Error fallback
            
            response = {
                "predictions": predictions
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode('utf-8'))
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"status": "ML Service Ready (Vercel Mode)"}).encode('utf-8'))
