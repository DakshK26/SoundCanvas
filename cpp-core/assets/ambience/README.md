# Ambience Audio Assets

This directory contains loopable ambient audio samples used to enhance the musical output.

## Required Files

Place the following WAV files in this directory (16-bit PCM, 44.1kHz, mono or stereo):

- `ocean.wav` - Loopable ocean waves sound
- `rain.wav` - Loopable rain sound
- `forest.wav` - Forest ambience with birds/insects
- `city.wav` - Distant traffic and urban hum
- `room.wav` - Subtle room tone / air noise

## Sources for Free Ambience Samples

You can obtain these from:
- Freesound.org (CC0 or CC-BY licensed)
- BBC Sound Effects (many are free for personal use)
- Generate simple ones using Audacity or similar tools

## File Specifications

- Sample Rate: 44100 Hz
- Bit Depth: 16-bit PCM
- Channels: Mono preferred (stereo will be converted)
- Duration: 5-30 seconds (will be looped)
- Format: WAV (uncompressed)

## Temporary Fallback

If these files are missing, the engine will generate simple procedural ambience or silence.
