# 🎵 SoundCanvas

**Built by Karan Kardam and Daksh Khanna**

**Turn your images into original ambient music.**

SoundCanvas is an AI-powered music generation platform that transforms images into unique musical compositions. Upload an image, select a genre, and let the system create an original track inspired by the visual features of your photo.

---

## 🌟 Features

- **🖼️ Image-to-Music Generation**: Upload any image and generate a unique musical composition
- **🎼 Multiple Genres**: RAP, HOUSE, R&B, EDM (Chill/Drop), RetroWave, or Auto-detect
- **🤖 Dual Generation Modes**: 
  - ML Model (AI-driven analysis)
  - Heuristic (rule-based generation)
- **🎚️ Professional Audio Production**: Multi-stem mixing, mastering, and sidechain compression
- **📊 Real-time Status**: Live generation progress tracking
- **📜 Generation History**: Browse and replay all your past creations
- **🎧 Built-in Audio Player**: Stream and download your tracks
- **☁️ AWS S3 Integration**: Scalable cloud storage for images and audio

---

## 🏗️ Architecture

SoundCanvas is built as a microservices architecture with the following components:

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend                             │
│         (Next.js + React + TypeScript + GraphQL)            │
└──────────────────────┬──────────────────────────────────────┘
                       │ GraphQL API
┌──────────────────────▼──────────────────────────────────────┐
│                   GraphQL Gateway                           │
│         (Node.js + TypeScript + Apollo Server)              │
│  • Image upload (S3 pre-signed URLs)                        │
│  • Job orchestration                                        │
│  • Database management (MySQL)                              │
└─┬────────────────┬──────────────────┬────────────────────┬──┘
  │                │                  │                    │
  ▼                ▼                  ▼                    ▼
┌────────┐  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐
│ C++    │  │ TensorFlow  │  │ Audio        │  │ Audio        │
│ Core   │  │ Serving     │  │ Renderer     │  │ Producer     │
│        │  │             │  │              │  │              │
│ • MIDI │  │ • ML Model  │  │ • FluidSynth │  │ • Mixing     │
│ • Genre│  │ • Feature   │  │ • MIDI→WAV   │  │ • Mastering  │
│        │  │   Mapping   │  │              │  │ • Multi-stem │
└────────┘  └─────────────┘  └──────────────┘  └──────────────┘
```

---

## 📦 Services

### 1. **Frontend** (`frontend/`)
- **Tech**: Next.js 14, React, TypeScript, Tailwind CSS, shadcn/ui
- **Features**:
  - Landing page with marketing content
  - Playground for image upload and generation
  - Real-time status polling
  - Audio player with download
  - Generation history with pagination
- **Port**: `3000`

### 2. **GraphQL Gateway** (`gateway/`)
- **Tech**: Node.js, TypeScript, Apollo Server, MySQL
- **Responsibilities**:
  - GraphQL API endpoint
  - S3 pre-signed URL generation
  - Job orchestration and status management
  - Database operations
- **Port**: `4000`

### 3. **C++ Core** (`cpp-core/`)
- **Tech**: C++17, CMake, libcurl, RtMidi
- **Responsibilities**:
  - Image feature extraction
  - MIDI composition generation
  - Genre template application
  - TensorFlow Serving integration
- **Port**: `8080`

### 4. **TensorFlow Serving** (`ml/`)
- **Tech**: Python, TensorFlow
- **Responsibilities**:
  - ML model serving
  - Image feature → music parameter mapping
- **Port**: `8501`

### 5. **Audio Renderer** (`audio-renderer/`)
- **Tech**: Python, Flask, FluidSynth
- **Responsibilities**:
  - MIDI to WAV rendering
  - Simple audio synthesis
- **Port**: `9000`

### 6. **Audio Producer** (`audio-producer/`)
- **Tech**: Python, Flask, FluidSynth, scipy, numpy
- **Responsibilities**:
  - Multi-stem MIDI rendering
  - Professional mixing with genre-aware settings
  - Sidechain compression
  - Mastering chain (EQ, compression, limiting)
  - LUFS normalization (-14 LUFS target)
  - Sample-based drums
- **Port**: `9001`

---

## 🚀 Quick Start

### Prerequisites

- **Docker** & **Docker Compose**
- **Node.js 18+** and npm
- **AWS Account** (for S3 storage)
- **Git**

### 1. Clone the Repository

```bash
git clone https://github.com/DakshK26/SoundCanvas.git
cd SoundCanvas
```

### 2. Configure Environment Variables

Create AWS credentials file:
```bash
# In SoundCanvas root directory
cat > aws_credentials.txt << EOF
AWS_REGION=us-east-2
S3_BUCKET_NAME=your-bucket-name
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
EOF
```

Create gateway environment file:
```bash
cd infra
cp .env.example .env
# Edit .env with your AWS credentials
```

### 3. Start Backend Services

```bash
cd infra
docker-compose up -d
```

This starts:
- Gateway (port 4000)
- C++ Core (port 8080)
- TensorFlow Serving (port 8501)
- Audio Renderer (port 9000)
- Audio Producer (port 9001)
- MySQL Database (port 3306)

### 4. Start Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend will be available at: **http://localhost:3000**

### 5. Verify Services

Check all services are healthy:
```bash
docker ps
# All containers should show (healthy) status
```

Test the GraphQL endpoint:
```bash
curl http://localhost:4000/graphql
```

---

## 🎮 Usage

### Generate Your First Track

1. **Open the app**: Navigate to http://localhost:3000
2. **Upload an image**: Drag & drop or click to browse
3. **Select genre**: Choose from dropdown or use "Auto (AI decides)"
4. **Choose mode**: ML Model (recommended) or Heuristic
5. **Click "Generate Track"**: Wait for the magic to happen!
6. **Play & Download**: Use the built-in player or download the WAV file

### View Generation History

1. Click the "History" tab in the Playground
2. Browse all your past generations
3. Click ▶️ to play or ⬇️ to download

---

## 🛠️ Development

### Project Structure

```
SoundCanvas/
├── frontend/              # Next.js React frontend
├── gateway/               # GraphQL API gateway
├── cpp-core/              # C++ audio engine
├── ml/                    # TensorFlow ML models
├── audio-renderer/        # MIDI → WAV service
├── audio-producer/        # Mixing & mastering service
├── infra/                 # Docker Compose & Terraform
├── scripts/               # Utility scripts
└── docs/                  # Documentation
```

### Running Individual Services

**Frontend:**
```bash
cd frontend
npm run dev
```

**Gateway:**
```bash
cd gateway
npm install
npm run build
npm start
```

**C++ Core:**
```bash
cd cpp-core
./build/soundcanvas_core --serve
```

### Database Migrations

The gateway automatically creates tables on startup. To reset:

```bash
docker-compose down
docker volume rm infra_soundcanvas-db
docker-compose up -d
```

---

## 🧪 Testing

### Test Full Pipeline

```bash
cd scripts
./test_full_pipeline.sh
```

### Test Individual Services

```bash
# Test gateway
curl -X POST http://localhost:4000/graphql \
  -H "Content-Type: application/json" \
  -d '{"query": "{ __typename }"}'

# Test cpp-core
curl http://localhost:8080/health

# Test audio-producer
curl http://localhost:9001/health
```

---

## 📚 API Documentation

### GraphQL Schema

**Mutations:**
- `requestImageUpload`: Get S3 pre-signed URL for image upload
- `generateTrack`: Start music generation from uploaded image
- `deleteGeneration`: Remove a generation from history

**Queries:**
- `getGeneration`: Get single generation by ID
- `listGenerations`: Get paginated generation history
- `getDownloadUrl`: Get pre-signed URL for audio download

**Subscriptions:**
- `generationUpdated`: Real-time status updates

See `gateway/src/schema.graphql` for full schema.

### REST Endpoints

**Audio Producer** (`POST /produce`):
```json
{
  "midi_path": "/data/audio/composition.mid",
  "output_path": "/data/audio/output.wav",
  "genre": "RetroWave",
  "apply_mastering": true,
  "use_sample_drums": true,
  "render_fx": true
}
```

---

## 🚢 Deployment

### AWS Deployment

See `PHASE10_AWS_DEPLOYMENT.md` for detailed AWS setup instructions.

Key steps:
1. Set up ECS cluster
2. Configure RDS for MySQL
3. Set up S3 buckets (images + audio)
4. Deploy services via Terraform
5. Configure domain and SSL

### Environment Variables

**Production .env:**
```bash
# AWS
AWS_REGION=us-east-2
S3_BUCKET_NAME=soundcanvas-uploads
AWS_ACCESS_KEY_ID=***
AWS_SECRET_ACCESS_KEY=***

# Database
DB_HOST=your-rds-endpoint
DB_PORT=3306
DB_USER=soundcanvas
DB_PASSWORD=***
DB_NAME=soundcanvas

# Services
CPP_SERVICE_URL=http://cpp-core:8080
SC_AUDIO_PRODUCER_URL=http://audio-producer:9001
SC_AUDIO_RENDERER_URL=http://audio-renderer:9000

# Frontend
NEXT_PUBLIC_GRAPHQL_ENDPOINT=https://api.yourdomain.com/graphql
```

---

## 🐛 Troubleshooting

### Common Issues

**"Generation failed: connect ECONNREFUSED"**
- Make sure all Docker services are running: `docker-compose ps`
- Check service logs: `docker logs infra-gateway-1`

**"Request failed with status code 404/500"**
- Verify audio-producer is healthy: `docker logs infra-audio-producer-1`
- Check endpoint configuration in gateway

**Database connection errors**
- Wait for MySQL to fully start (can take 30 seconds)
- Verify DB credentials in docker-compose.yml

**Audio files are silent or corrupted**
- Check FluidSynth soundfont is installed in containers
- Verify MIDI files are being generated correctly

### Logs

View service logs:
```bash
# All services
docker-compose logs -f

# Specific service
docker logs infra-gateway-1 -f
docker logs infra-audio-producer-1 -f
docker logs infra-cpp-core-1 -f
```

---

## 📄 License

See `LICENSE` file for details.

---

## 🤝 Contributing

This is a course project. Contributions guidelines TBD.

---

## 📞 Support

For issues or questions:
- Check documentation in `/docs` folder
- Review phase implementation guides
- Check service-specific READMEs

---

## 🎉 Acknowledgments

- **FluidSynth** for MIDI synthesis
- **TensorFlow** for ML capabilities
- **shadcn/ui** for beautiful UI components
- **Next.js** team for the amazing framework

---

**Built with ❤️ by the SoundCanvas team**
