# Audio Renderer Service

FluidSynth-based MIDI to WAV renderer with ambience mixing support.

## Features

- Renders MIDI files to high-quality WAV using FluidR3_GM soundfont
- Optional ambience layer mixing (ocean, rain, forest, city)
- Mood-based ambience volume control
- Docker-containerized for easy deployment

## API

### POST /render

Render a MIDI file to WAV with optional ambience.

**Request:**
```json
{
  "midi_path": "/data/midi/ocean.mid",
  "output_path": "/data/audio/ocean.wav",
  "ambience_type": "ocean",
  "mood_score": 0.8
}
```

**Response:**
```json
{
  "status": "success",
  "output_path": "/data/audio/ocean.wav",
  "file_size": 1234567,
  "ambience_applied": true
}
```

**Parameters:**
- `midi_path` (required): Path to input MIDI file
- `output_path` (required): Path for output WAV file
- `ambience_type` (optional): One of `none`, `ocean`, `rain`, `forest`, `city` (default: `none`)
- `mood_score` (optional): 0.0-1.0, controls ambience volume (default: 0.5)

### GET /health

Health check endpoint.

## Local Development

```bash
# Build
docker build -t soundcanvas-audio-renderer .

# Run
docker run -p 9000:9000 \
  -v $(pwd)/../data:/data \
  soundcanvas-audio-renderer
```

## Ambience Files

Place ambience WAV files in `/data/ambience/`:
- `ocean.wav` - Ocean waves
- `rain.wav` - Rain sounds  
- `forest.wav` - Forest ambience
- `city.wav` - Urban sounds

These are optional - if missing, ambience mixing is skipped.

## Soundfont

The service downloads FluidR3_GM.sf2 automatically during build.
Alternative soundfonts can be mounted to `/sf/` and specified via `SF2_PATH` environment variable.
