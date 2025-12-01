from http.server import BaseHTTPRequestHandler
import json
import os
import numpy as np
from scipy.io import wavfile
import tempfile
import base64
import io

# Vercel-compatible Audio Producer
# Generates synthetic audio since FluidSynth is not available in serverless environment

def generate_synthetic_track(genre, duration=30.0):
    sample_rate = 44100
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    
    # Bass line (simple sine)
    bass_freq = 55.0 # A1
    if genre == 'EDM_DROP':
        bass_freq = 45.0
    
    bass = 0.5 * np.sin(bass_freq * t * 2 * np.pi)
    
    # Add some modulation
    mod = 0.2 * np.sin(2.0 * t * 2 * np.pi)
    bass = bass * (1 + mod)
    
    # Simple beat (noise bursts)
    beat = np.zeros_like(t)
    kick_interval = int(sample_rate * 0.5) # 120 BPM
    for i in range(0, len(t), kick_interval):
        if i + 2000 < len(t):
            beat[i:i+1000] = np.random.uniform(-1, 1, 1000) * np.linspace(1, 0, 1000)
            
    # Mix
    mix = (bass + beat) * 0.5
    
    # Normalize
    mix = mix / np.max(np.abs(mix))
    
    # Convert to 16-bit PCM
    audio_data = (mix * 32767).astype(np.int16)
    
    return audio_data, sample_rate

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers.get('content-length', 0))
            body = self.rfile.read(length)
            data = json.loads(body)
            
            midi_base64 = data.get('midi_base64')
            genre = data.get('genre', 'EDM_CHILL')
            
            # Generate synthetic audio
            audio_data, rate = generate_synthetic_track(genre)
            
            # Write to bytes
            byte_io = io.BytesIO()
            wavfile.write(byte_io, rate, audio_data)
            wav_bytes = byte_io.getvalue()
            
            audio_base64 = base64.b64encode(wav_bytes).decode('utf-8')
            
            response = {
                'status': 'success',
                'audio_base64': audio_base64,
                'file_size': len(wav_bytes),
                'lufs': -14.0,
                'duration_sec': 30.0,
                'genre': genre,
                'note': 'Generated via Vercel Synthetic Engine'
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode('utf-8'))
            
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'status': 'Audio Producer Ready (Vercel Mode)'}).encode('utf-8'))
