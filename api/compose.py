import os
import json
import base64
from http.server import BaseHTTPRequestHandler

# Vercel-compatible C++ Core Wrapper
# Simulates the C++ composition engine

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers.get('content-length', 0))
            body = self.rfile.read(length)
            data = json.loads(body)
            
            # Accept image_base64 or image_path
            image_base64 = data.get('image_base64')
            
            # Mock MIDI generation (Minimal valid MIDI file)
            # Header Chunk: MThd, len 6, format 0, 1 track, 480 ticks/beat
            # Track Chunk: MTrk, len ...
            mock_midi_b64 = 'TVRoZAAAAAYAAQABAfAAV1RyawAAAAcADGkAAP8D'
            
            response = {
                'status': 'success',
                'midi_base64': mock_midi_b64,
                'tempo_bpm': 120,
                'scale_type': 'minor',
                'decided_genre': data.get('genre', 'EDM_CHILL'),
                'note': 'Generated via Vercel Core Mock'
            }
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
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
        self.wfile.write(json.dumps({'status': 'Core Service Ready (Vercel Mode)'}).encode('utf-8'))
