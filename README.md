# SoundCanvas  
### AI-Powered Image → Music Generation System  
*C++17 • TensorFlow • Python DSP • Next.js • GraphQL • Docker • AWS S3/ECS/RDS (PostgreSQL)*

---

## Overview

SoundCanvas is a full-stack, cloud-native system that transforms any input image into a fully mixed, mastered instrumental track.  
It combines machine learning, algorithmic music theory, digital signal processing, and a distributed microservice architecture deployed on AWS.

The system analyzes visual features, predicts musical parameters using TensorFlow, composes structured multi-genre MIDI, renders audio using a Python DSP engine with sample-based drums and FX, and delivers professionally mixed tracks through a modern web interface.

---

# System Goals

- Convert images into high-quality instrumental tracks  
- Provide musical diversity across Rap, House, R&B, EDM, and Chill genres  
- Use machine learning to map visual features into musical expression  
- Generate production-ready audio (mastered to -14 LUFS)  
- Run as a scalable, secure, containerized cloud platform  
- Support browser-based user interaction with direct S3 uploads  

---

# Monorepo Layout
soundcanvas/
│
├── cpp-core/                      # C++17 composition engine
│   ├── include/
│   ├── src/
│   └── build/
│
├── ml/                            # TensorFlow model + serving
│   ├── src/
│   ├── data/
│   └── models/exported_model_versioned/
│
├── audio-producer/                # Python DSP microservice
│   ├── drum_sampler.py
│   ├── fx_player.py
│   ├── stem_mixer.py
│   ├── mastering.py
│   └── assets/
│
├── gateway/                       # GraphQL API (Node.js / TypeScript)
│   ├── schema.ts
│   ├── resolvers/
│   └── orchestrator.ts
│
├── frontend/                      # Next.js UI
│   ├── components/
│   └── pages/
│
├── infra/                         # Docker & Terraform infrastructure
│   ├── docker-compose.yml
│   ├── terraform/
│   └── ecr_push.sh
│
└── docs/                          # Architecture & phase documentation

# AWS Deployment Architecture

                     ┌─────────────────────────────┐
                     │         Client Browser       │
                     └──────────────┬───────────────┘
                                    │ HTTPS
                                    ▼
                     ┌─────────────────────────────┐
                     │    Frontend (Next.js App)    │
                     │  (e.g., served via S3/CF)    │
                     └──────────────┬───────────────┘
                                    │ GraphQL HTTPS
                                    ▼
                     ┌─────────────────────────────┐
                     │  API Gateway (ECS Service)   │
                     │ Apollo GraphQL + TypeScript  │
                     └──────────────┬───────────────┘
                                    │
         ┌──────────────────────────┼───────────────────────────┐
         │                          │                           │
         │                    Pre-signed S3 URLs                │
         │                          │                           │
         ▼                          ▼                           ▼
 ┌─────────────────┐       ┌─────────────────┐         ┌─────────────────────┐
 │ AWS S3 (Images) │       │ AWS S3 (Audio) │         │ AWS RDS PostgreSQL   │
 └─────────────────┘       └─────────────────┘         │ Job & user metadata │
                                                       └─────────────────────┘

      Orchestrator (Node.js ECS Task)
               │
               ▼
 ┌───────────────────────────────┐
 │   Backend ECS Services        │
 │                               │
 │  • TensorFlow Inference       │
 │  • C++ Composition Engine     │
 │  • Python Audio Producer      │
 └───────────────────────────────┘

 Logs & Metrics:
   • CloudWatch Logs for all ECS tasks
   • Application-level logging from C++, Node.js, and Python


**Inputs:**  
`[avgR, avgG, avgB, brightness, hue, saturation, colorfulness, contrast]`  

**Outputs:**  
`[tempo, baseFrequency, energy, timbreBrightness, reverb, scaleType, patternType]`  

---

## 2. **C++17 Composition Engine**
- Extracts visual features using stb_image  
- Communicates with the TensorFlow inference service  
- Chooses genre: Rap, House, R&B, EDM Chill, EDM Drop  
- Builds full song structure:
  - Intro → Section A → Section B → Outro  
- Implements:
  - Chord progressions  
  - Melodic phrases  
  - Syncopation, swing, groove templates  
  - Drum pattern logic  

**Output:** Multi-track MIDI (Format 1)

---

## 3. **Python DSP Engine (Audio Producer)**
- Sample-based drums using Freesound API kits (Trap 808, House, R&B Soft)  
- Instrument rendering via FluidSynth  
- Precise MIDI-based sidechain compression  
- FX system:
  - Risers  
  - Sweeps  
  - Impacts  
- Mixing:
  - Per-genre EQ and compression  
  - Stereo widening  
  - Convolution reverb  
- Mastering chain to streaming loudness (-14 LUFS)  

**Output:** Fully mixed WAV file

---

## 4. **GraphQL Gateway**
- Built with Apollo Server + TypeScript  
- Provides pre-signed URLs for direct S3 uploads  
- Stores job state in PostgreSQL  
- Initiates pipeline processing  
- Queries for status, history, and final audio URLs  

**Key Mutations & Queries:**  
- `createGeneration`  
- `startGeneration`  
- `generationStatus`  
- `myGenerations`  

---

## 5. **Frontend (Next.js + Tailwind + GraphQL)**
- Drag-and-drop image upload  
- Uploads directly to S3 via pre-signed URL  
- Displays real-time status from GraphQL polling  
- Streams final audio directly from S3  
- Includes generation history page  

---

# Cloud Infrastructure (AWS)

**Provisioned using Terraform**  

### Components:
- **ECS Fargate**  
  - C++ Engine container  
  - Python DSP container  
  - TensorFlow inference container  
  - GraphQL gateway container  

- **S3**  
  - Raw uploaded images  
  - Final WAV audio files  

- **RDS PostgreSQL**  
  - Job metadata  
  - Generation history  
  - Status tracking  

- **ECR**
  - Stores all container images  

- **IAM + Secret Management**
  - Least-privilege execution roles  
  - Environment variables only (never stored in Git)  

- **CloudWatch Logs**
  - Full centralized logging  

---

# Technologies Used and What They Do

### Machine Learning
- **TensorFlow**: Predict musical parameters from image features  
- **NumPy / Python**: Preprocessing and dataset generation  

### Algorithmic Composition (C++)
- **CMake + C++17**: High-performance feature extraction & composition  
- **stb_image**: Image decoding  
- **nlohmann/json**: API communication  
- **httplib**: Microservice requests  
- **Custom Theory Engine**: Chords, scales, tempo mapping  

### Audio Production (Python)
- **FluidSynth**: Instrument rendering  
- **soundfile / librosa**: Audio manipulation  
- **Custom DSP**: Mastering, FX, sidechain  
- **Freesound API**: Sample retrieval  

### Web Back-End
- **Node.js + TypeScript**  
- **Apollo GraphQL Server**  
- **AWS SDK v3** for S3, RDS, Secrets  

### Front-End
- **Next.js / React**  
- **TailwindCSS**  
- **Apollo Client**  

### Cloud & DevOps
- **AWS ECS Fargate**: Microservice execution  
- **AWS RDS PostgreSQL**: Persistent data  
- **AWS S3**: File storage  
- **AWS ECR**: Image registry  
- **Terraform**: Infrastructure-as-code  
- **Docker / Docker Compose**: Local microservice graph  

---

# What the Project Accomplishes

SoundCanvas achieves a fully automated, production-quality pipeline from image to music:

1. **Understands visual content**  
2. **Predicts expressive musical parameters**  
3. **Composes structured, multi-genre MIDI**  
4. **Renders realistic instruments using sample libraries**  
5. **Applies professional mixing and mastering**  
6. **Runs on scalable cloud infrastructure**  
7. **Delivers music directly to users through a modern web interface**

This creates a generative system capable of producing **full-length, cohesive, genre-varied instrumentals** directly from images.

---

# Acknowledgements

This project integrates principles from music information retrieval, DSP engineering, distributed systems, ML model serving, and cloud architecture.

All components are custom-built and modular to support future extensions such as:
- More genres  
- Recurrent musical motifs  
- Style transfer  
- Real-time generation  
- User accounts and playlists  

---

# License

MIT License.
