# Audio Producer Service - Multi-stem Mixing & Mastering

## Overview

The **audio-producer** service is a Flask-based microservice that takes multiple MIDI instrument stems and produces a professional-quality, mixed and mastered WAV file ready for playback. It implements:

- **Multi-stem rendering** - Each MIDI instrument rendered separately via FluidSynth
- **Professional mixing** - Stem-level volume balancing with EDM mixing guidelines
- **Sidechain compression** - EDM-style ducking on bass/pads when kick hits
- **Mastering chain** - 3-stage EQ → Compression → Limiting pipeline
- **Loudness normalization** - Targets -14 LUFS for consistent playback volume

## Architecture

```
Person A's Composition Engine
    ↓
Multiple MIDI files (kick.mid, bass.mid, lead.mid, etc.)
    ↓
Audio Producer Service:
    1. Render each MIDI → WAV stem (FluidSynth)
    2. Mix stems with proper gain staging
    3. Apply sidechain ducking (kick → bass/pads)
    4. Mastering chain:
       - EQ (bass boost, mid scoop, high shelf)
       - Compression (4:1 ratio, -18dB threshold)
       - Limiting (prevent clipping, normalize to -14 LUFS)
    ↓
Final WAV output (44.1kHz, 16-bit stereo)
```

## Service Endpoints

### POST `/produce`

Main production endpoint - full mixing and mastering pipeline.

**Request:**
```json
{
  "stems": {
    "kick": "/data/midi/kick.mid",
    "snare": "/data/midi/snare.mid",
    "bass": "/data/midi/bass.mid",
    "lead": "/data/midi/lead.mid",
    "pad": "/data/midi/pad.mid"
  },
  "output_path": "/data/audio/final.wav",
  "genre": "EDM_Drop",
  "apply_mastering": true,
  "apply_sidechain": true,
  "sidechain_targets": ["bass", "lead", "pad"]
}
```

**Parameters:**
- `stems` (object) - Map of stem name → MIDI file path
- `output_path` (string) - Output WAV file path
- `genre` (string, optional) - Genre template (default: "EDM_Drop")
- `apply_mastering` (bool, optional) - Apply mastering chain (default: true)
- `apply_sidechain` (bool, optional) - Apply sidechain compression (default: true)
- `sidechain_targets` (array, optional) - Stems to apply sidechain to (default: ["bass", "lead", "pad"])

**Response:**
```json
{
  "status": "success",
  "output_path": "/data/audio/final.wav",
  "file_size": 5242880,
  "lufs": -14.2,
  "duration_sec": 67.5,
  "stems_count": 5,
  "mastering_applied": true,
  "sidechain_applied": true
}
```

### POST `/render-stem`

Simple endpoint to render single MIDI → WAV (no mixing/mastering).

**Request:**
```json
{
  "midi_path": "/data/midi/kick.mid",
  "output_path": "/data/stems/kick.wav"
}
```

**Response:**
```json
{
  "status": "success",
  "output_path": "/data/stems/kick.wav",
  "file_size": 1048576
}
```

### GET `/health`

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "audio-producer"
}
```

## Mixing Pipeline Details

### 1. Stem Rendering (FluidSynth)

Each MIDI file is rendered separately using FluidSynth with the FluidR3_GM soundfont:

```bash
fluidsynth -ni -g 1.0 -r 44100 FluidR3_GM.sf2 input.mid -F output.wav -O s16
```

- Sample rate: 44.1kHz
- Output format: 16-bit PCM
- Stereo output

### 2. Stem Mixing

Stems are mixed according to **EDM mixing guidelines**:

| Stem | Default Gain | Role |
|------|--------------|------|
| kick | 1.0 (0dB) | Reference level - loudest element |
| snare | 0.8 (-2dB) | Slightly below kick |
| hihat | 0.5 (-6dB) | Background rhythm |
| bass | 0.9 (-1dB) | Almost as loud as kick |
| lead | 0.7 (-3dB) | Prominent but not overpowering |
| pad | 0.4 (-8dB) | Atmospheric layer |
| arp | 0.6 (-4dB) | Mid-level texture |
| fx | 0.3 (-10dB) | Subtle effects |

After mixing, the signal is normalized to **0.8 peak** to leave **0.2 headroom** for mastering.

### 3. Sidechain Compression

**EDM-style pumping effect** where bass/pads "duck" when the kick hits:

**Process:**
1. Extract kick stem audio
2. Detect kick envelope (peak detection + smoothing)
3. Create ducking curve: `1.0 - (envelope * 0.6)` (60% ducking depth)
4. Apply curve to specified stems (bass, lead, pad)

**Effect:**
- When kick hits (envelope = 1.0): target stems reduced to 40% volume
- When kick silent (envelope = 0.0): target stems at 100% volume
- Creates rhythmic "pumping" characteristic of EDM

**Implementation:**
```python
# Kick envelope detection
envelope = abs(kick_audio)
envelope = gaussian_filter1d(envelope, sigma=441)  # 10ms smoothing
envelope = envelope / envelope.max()

# Create ducking curve
ducking = 1.0 - (envelope * 0.6)

# Apply to target stems
bass_ducked = bass_audio * ducking
```

### 4. Mastering Chain

3-stage mastering using ffmpeg audio filters to achieve professional loudness and prevent clipping.

#### Stage 1: EQ
```
equalizer=f=100:t=h:width=200:g=3     # +3dB bass boost at 100Hz
equalizer=f=500:t=h:width=400:g=-2    # -2dB mid scoop at 500Hz
equalizer=f=8000:t=h:width=2000:g=2   # +2dB high shelf at 8kHz
```

**Purpose:**
- Bass boost: EDM punch and power
- Mid scoop: Clear out "muddy" frequencies
- High boost: Air and brightness

#### Stage 2: Compression
```
acompressor=threshold=-18dB:ratio=4:attack=5:release=50:makeup=6dB
```

**Purpose:**
- Control dynamics (4:1 ratio)
- Let transients through (5ms attack)
- Pumping feel (50ms release)
- Increase overall loudness (+6dB makeup gain)

#### Stage 3: Limiting + Loudness Normalization
```
loudnorm=I=-14:LRA=7:tp=-0.1    # Normalize to -14 LUFS
alimiter=limit=0.99:attack=1:release=50  # Prevent clipping
```

**Purpose:**
- Normalize to **-14 LUFS** (Spotify/YouTube standard)
- True peak limiting at -0.1dB (prevent inter-sample clipping)
- Consistent loudness across all generated tracks

**Target Metrics:**
- Integrated loudness: **-14 LUFS**
- True peak: **-0.1dB**
- Loudness range: **7 LU**

## C++ Integration

### AudioProducerClient

C++ client for calling the audio-producer service from the cpp-core.

**Header:** `cpp-core/include/AudioProducerClient.hpp`

**Usage Example:**
```cpp
#include "AudioProducerClient.hpp"

// Initialize client
AudioProducerClient producer("http://audio-producer:9001");

// Check if service is up
if (!producer.healthCheck()) {
    std::cerr << "Audio producer service not available" << std::endl;
    return false;
}

// Prepare stems (from Person A's composition engine)
std::map<std::string, std::string> stems = {
    {"kick", "/data/midi/kick.mid"},
    {"snare", "/data/midi/snare.mid"},
    {"bass", "/data/midi/bass.mid"},
    {"lead", "/data/midi/lead.mid"},
    {"pad", "/data/midi/pad.mid"}
};

// Produce final track
bool success = producer.produceTrack(
    stems,
    "/data/audio/final.wav",
    "EDM_Drop",                        // genre
    true,                              // apply mastering
    true,                              // apply sidechain
    {"bass", "lead", "pad"}            // sidechain targets
);

if (success) {
    std::cout << "Track produced successfully!" << std::endl;
}
```

**Methods:**

- `produceTrack()` - Full mixing/mastering pipeline
- `renderStem()` - Single MIDI → WAV (no mixing)
- `healthCheck()` - Service availability check

## Docker Configuration

### Dockerfile

Based on Python 3.11 with system dependencies:
- **fluidsynth** - MIDI synthesizer
- **ffmpeg** - Audio processing (mastering filters)
- **libsndfile1** - WAV file I/O

Python dependencies:
- **flask** 3.0.0 - Web framework
- **numpy** 1.24.3 - Audio array operations
- **scipy** 1.11.3 - Signal processing (resampling, filtering)
- **pydub** 0.25.1 - Audio manipulation utilities

### Environment Variables

- `SF2_PATH` - Path to soundfont file (default: `/sf/FluidR3_GM.sf2`)

### Volumes

- `/data` - Shared volume for MIDI/audio files

### Ports

- `9001` - HTTP service port

## Integration with Phase 8

### Person A Responsibilities

Person A's composition engine will:
1. Generate `SongSpec` from image features
2. Create MIDI files for each instrument (kick, snare, bass, lead, etc.)
3. Save MIDIs to `/data/midi/`
4. Call Person B's `AudioProducerClient`

### Person B Responsibilities (THIS IMPLEMENTATION) ✅

Person B's audio producer:
1. Accept MIDI stems from Person A
2. Render each stem via FluidSynth
3. Mix stems with proper gain staging
4. Apply sidechain compression
5. Apply mastering chain (EQ → Comp → Limiter)
6. Return professional-quality WAV

### Data Flow

```
Image → Features → ML Model → StyleVector
                        ↓
              [Person A: Composition]
         Genre Template + Section Plan
                        ↓
           MIDI Generation (per instrument)
         /data/midi/kick.mid, bass.mid, etc.
                        ↓
              [Person B: Production] ← YOU ARE HERE
         AudioProducerClient.produceTrack()
                        ↓
         FluidSynth rendering (parallel)
                        ↓
         Stem mixing + Sidechain
                        ↓
         Mastering chain
                        ↓
         /data/audio/final.wav (-14 LUFS, ready to play)
```

## Testing

### Manual Testing

1. **Build the service:**
   ```bash
   cd audio-producer
   docker build -t soundcanvas-audio-producer .
   ```

2. **Run standalone:**
   ```bash
   docker run -p 9001:9001 -v /path/to/data:/data soundcanvas-audio-producer
   ```

3. **Test with curl:**
   ```bash
   # Health check
   curl http://localhost:9001/health
   
   # Produce track (need MIDI files first)
   curl -X POST http://localhost:9001/produce \
     -H "Content-Type: application/json" \
     -d '{
       "stems": {
         "kick": "/data/midi/kick.mid",
         "bass": "/data/midi/bass.mid"
       },
       "output_path": "/data/audio/test.wav",
       "apply_mastering": true,
       "apply_sidechain": true
     }'
   ```

### Integration Testing

1. Start full stack:
   ```bash
   cd infra
   docker-compose up --build
   ```

2. Wait for Person A's composition engine

3. Test with image:
   ```bash
   curl -X POST http://localhost:4000/graphql \
     -F operations='{"query":"mutation($file:Upload!){uploadImage(file:$file){id url audioUrl}}"}' \
     -F map='{"0":["variables.file"]}' \
     -F 0=@test_image.jpg
   ```

4. Verify output:
   - Check `/data/audio/` for final WAV
   - Measure LUFS: should be around -14
   - Listen: clear structure, good mix, no clipping

### Quality Metrics

- ✅ No clipping (true peak < -0.1dB)
- ✅ Consistent loudness (-14 LUFS ± 1)
- ✅ Audible sidechain pumping on bass/pads
- ✅ Clear separation between stems
- ✅ Punchy kick and snare
- ✅ Clean high end (no harshness)

## File Structure

```
audio-producer/
├── Dockerfile              # Container with FluidSynth + ffmpeg
├── requirements.txt        # Python dependencies
├── app.py                  # Flask service (main endpoints)
├── stem_mixer.py          # Stem mixing + sidechain logic
└── mastering.py           # EQ + Compression + Limiting

cpp-core/
├── include/
│   └── AudioProducerClient.hpp   # C++ client interface
└── src/
    └── AudioProducerClient.cpp   # C++ client implementation

infra/
└── docker-compose.yml      # Updated with audio-producer service
```

## Performance

### Rendering Time

Approximate times for 60-second track:

| Operation | Time |
|-----------|------|
| Render 5 MIDI stems | ~5s |
| Stem mixing + sidechain | ~1s |
| Mastering chain | ~2s |
| **Total** | **~8s** |

### Resource Usage

- CPU: Moderate (ffmpeg filters are CPU-intensive)
- Memory: ~200MB per request
- Disk I/O: Sequential writes (stems → mixed → mastered)

## Future Enhancements

### Possible Improvements

1. **Pre-rendered loops** - Use WAV loops instead of MIDI for certain stems (kicks, drums)
2. **Parallel rendering** - Render multiple stems simultaneously
3. **VST plugin support** - Add Helm or ZynAddSubFX for better synth sounds
4. **Stem caching** - Cache rendered stems if MIDI hasn't changed
5. **Advanced mastering** - Multi-band compression, stereo widening
6. **Genre-specific mastering** - Different EQ/compression per genre
7. **Real-time preview** - Stream partial renders during processing

### Known Limitations

1. **FluidSynth sounds** - GM soundfont is decent but not "pro" EDM quality
2. **Fixed mastering chain** - Same EQ/comp settings for all genres
3. **Simple sidechain** - Envelope-based, not true dynamic sidechain
4. **No stereo widening** - Output is stereo but not "wide"
5. **No parallel compression** - Common in EDM production

## Troubleshooting

### Service won't start

- Check soundfont exists: `ls -lh /sf/FluidR3_GM.sf2`
- Check ffmpeg installed: `ffmpeg -version`

### LUFS measurement fails

- ffmpeg's `loudnorm` filter requires recent version
- Fallback: simple limiter is applied instead

### Stems not rendering

- Check MIDI files exist and are valid
- Test FluidSynth manually: `fluidsynth -ni /sf/FluidR3_GM.sf2 test.mid -F out.wav`

### No sidechain effect

- Ensure `kick` stem is in the stems map
- Check kick MIDI has actual notes (not empty)
- Increase sidechain depth in `stem_mixer.py` (line ~89)

---

**Person B Phase 8 Implementation - COMPLETE** ✅

All audio production infrastructure is ready for Person A's composition engine integration.
