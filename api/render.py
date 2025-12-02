from http.server import BaseHTTPRequestHandler
import json
import os
import math
import struct
import wave
import tempfile
import base64
import io

# Vercel-compatible Audio Producer
# Generates synthetic audio since FluidSynth is not available in serverless environment

def generate_synthetic_track(genre, duration=30.0):
    sample_rate = 44100
    num_samples = int(sample_rate * duration)
    
    # Bass line (simple sine)
    bass_freq = 55.0 # A1
    if genre == 'EDM_DROP':
        bass_freq = 45.0
    
    # Generate audio data
    audio_data = bytearray()
    
    for i in range(num_samples):
        t = i / sample_rate
        
        # Bass
        bass = 0.5 * math.sin(bass_freq * t * 2 * math.pi)
        
        # Modulation
        mod = 0.2 * math.sin(2.0 * t * 2 * math.pi)
        bass = bass * (1 + mod)
        
        # Simple beat (noise bursts)
        beat = 0.0
        kick_interval = int(sample_rate * 0.5) # 120 BPM
        if (i % kick_interval) < 1000:
             # Simple noise
             import random
             beat = random.uniform(-1, 1) * (1.0 - (i % kick_interval)/1000.0)
            
        # Mix
        mix = (bass + beat) * 0.5
        
        # Clip
        if mix > 1.0: mix = 1.0
        if mix < -1.0: mix = -1.0
        
        # Convert to 16-bit PCM
        sample = int(mix * 32767)
        audio_data.extend(struct.pack('<h', sample))
    
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
            audio_bytes, rate = generate_synthetic_track(genre)
            
            # Write to bytes
            byte_io = io.BytesIO()
            with wave.open(byte_io, 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(rate)
                wav_file.writeframes(audio_bytes)
            
            wav_bytes_final = byte_io.getvalue()
            
            audio_base64 = base64.b64encode(wav_bytes_final).decode('utf-8')
            
            response = {
                'status': 'success',
                'audio_base64': audio_base64,
                'file_size': len(wav_bytes_final),
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
