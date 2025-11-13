# Phase 10 - Person B Implementation Guide

## ✅ Implementation Status: COMPLETE

This document describes the **Person B (Backend/Gateway/AWS)** implementation for Phase 10 of SoundCanvas.

---

## Overview

Person B is responsible for:
1. GraphQL schema & resolvers (Gateway)
2. S3 storage integration with pre-signed URLs
3. RDS MySQL database
4. Orchestrator service (Gateway → cpp-core → audio-producer)
5. AWS deployment (ECS, ALB, RDS, S3)

---

## B1. GraphQL Schema & Resolvers ✅

### Schema (`gateway/src/schema.ts`)

**Already implemented:**

```graphql
type Mutation {
  createGeneration(input: CreateGenerationInput!): CreateGenerationPayload!
  startGeneration(jobId: ID!): MutationResponse!
}

type Query {
  generationStatus(jobId: ID!): GenerationStatusResponse!
  myGenerations(limit: Int!): [Generation!]!
}

input CreateGenerationInput {
  genreOverride: String
  mode: String    # "model" | "heuristic"
}

type CreateGenerationPayload {
  jobId: ID!
  imageUploadUrl: String!   # Pre-signed S3 PUT URL
  imageId: String!
}

type GenerationStatusResponse {
  status: GenerationStatus!
  audioUrl: String           # Pre-signed S3 GET URL
  imageUrl: String
  params: GenerationParams
  errorMessage: String
}

type Generation {
  id: ID!
  userId: String
  imageKey: String!
  audioKey: String
  genre: String!
  tempoBpm: Float!
  status: GenerationStatus!
  errorMessage: String
  createdAt: String!
  imageUrl: String
  audioUrl: String
}

enum GenerationStatus {
  PENDING
  RUNNING
  COMPLETE
  FAILED
}
```

### Resolvers (`gateway/src/resolvers/`)

#### `Mutation.createGeneration`
1. Generate unique `jobId` (UUID)
2. Get user ID (or default to 'default-user')
3. Generate S3 pre-signed PUT URL for image upload
4. Create DB record with status=PENDING
5. Return `{ jobId, imageUploadUrl, imageId }`

#### `Mutation.startGeneration`
1. Update DB status to RUNNING
2. Trigger async `orchestrator.processGeneration(jobId)`
3. Return `{ success: true }`

#### `Query.generationStatus`
1. Fetch generation from DB by jobId
2. Generate pre-signed GET URLs for image and audio
3. Return status, URLs, params, errorMessage

#### `Query.myGenerations`
1. Fetch user's generations from DB (ordered by created_at DESC)
2. Generate pre-signed GET URLs for all images/audio
3. Return list with URLs

---

## B2. S3 Storage Service ✅

### Implementation (`gateway/src/services/storage.ts`)

```typescript
export class StorageService {
  // Generate pre-signed PUT URL (frontend uploads directly)
  async getImageUploadUrl(userId: string, jobId: string): Promise<string>
  
  // Generate pre-signed GET URL (frontend downloads/plays)
  async getImageReadUrl(key: string): Promise<string>
  async getAudioReadUrl(key: string): Promise<string>
  
  // S3 key helpers
  getImageKey(userId: string, jobId: string): string
  getAudioKey(userId: string, jobId: string): string
}
```

### S3 Bucket Structure
```
soundcanvas-uploads/
├── images/
│   └── {userId}/
│       └── {jobId}/
│           └── input.jpg
├── audio/
│   └── {userId}/
│       └── {jobId}/
│           └── output.wav
└── midi/
    └── {userId}/
        └── {jobId}/
            └── composition.mid
```

### Configuration

**Environment Variables:**
```bash
AWS_REGION=us-east-2
AWS_ACCESS_KEY_ID=<your-key>
AWS_SECRET_ACCESS_KEY=<your-secret>
S3_BUCKET_NAME=soundcanvas-uploads
USE_S3=true
```

**Bucket Policy (CORS):**
```json
{
  "CORSRules": [
    {
      "AllowedOrigins": ["http://localhost:3000", "https://soundcanvas.yourdomain.com"],
      "AllowedMethods": ["GET", "PUT", "HEAD"],
      "AllowedHeaders": ["*"],
      "ExposeHeaders": ["ETag"],
      "MaxAgeSeconds": 3000
    }
  ]
}
```

---

## B3. RDS MySQL Integration ✅

### Database Schema (`gateway/src/db.ts`)

```sql
CREATE TABLE generations (
  id VARCHAR(36) PRIMARY KEY,
  user_id VARCHAR(255) DEFAULT 'default-user',
  image_key VARCHAR(512) NOT NULL,
  audio_key VARCHAR(512),
  genre VARCHAR(50) NOT NULL,
  tempo_bpm FLOAT DEFAULT 0,
  mood FLOAT DEFAULT 0.5,
  scale_type VARCHAR(50),
  status ENUM('PENDING','RUNNING','COMPLETE','FAILED') NOT NULL DEFAULT 'PENDING',
  mode ENUM('heuristic','model') NOT NULL DEFAULT 'model',
  error_message TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  
  INDEX idx_user_created (user_id, created_at DESC),
  INDEX idx_status (status)
);
```

### Connection Configuration

**Environment Variables:**
```bash
# RDS (Production)
RDS_ENDPOINT=your-instance.us-east-2.rds.amazonaws.com:3306
RDS_USERNAME=admin
RDS_PASSWORD=<from-secrets-manager>
RDS_DB_NAME=soundcanvas
RDS_SSL=false

# Local (Development)
DB_HOST=localhost
DB_PORT=3306
DB_USER=soundcanvas
DB_PASSWORD=soundcanvas
DB_NAME=soundcanvas
```

### DB Functions

```typescript
insertGeneration(gen: {...}): Promise<void>
getGenerationById(id: string): Promise<Generation | null>
getUserGenerations(userId: string, limit: number): Promise<Generation[]>
updateGenerationStatus(id: string, status: string, updates?: {...}): Promise<void>
```

---

## B4. Orchestrator Service ✅

### Pipeline (`gateway/src/services/orchestrator.ts`)

The orchestrator manages the full generation pipeline:

```
1. Download image from S3
   ↓
2. Call cpp-core service (POST /generate)
   - Send image data (base64 or file)
   - Get MIDI path, tempo, scale
   ↓
3. Call audio-producer service (POST /render)
   - Send MIDI path
   - Get WAV path
   ↓
4. Upload WAV to S3
   ↓
5. Update DB status to COMPLETE
```

### Implementation

```typescript
export class OrchestratorService {
  async processGeneration(jobId: string): Promise<void> {
    // 1. Fetch generation from DB
    const generation = await getGenerationById(jobId);
    
    // 2. Download image from S3 to temp file
    await this.downloadFromS3(generation.image_key, imagePath);
    
    // 3. Call cpp-core
    const cppResponse = await this.callCppCore(
      imagePath, 
      generation.genre, 
      generation.mode
    );
    
    // 4. Call audio-producer
    await this.callAudioProducer(cppResponse.midiPath, audioPath);
    
    // 5. Upload audio to S3
    const audioKey = `audio/${userId}/${jobId}/output.wav`;
    await this.uploadToS3(audioPath, audioKey, 'audio/wav');
    
    // 6. Update DB
    await updateGenerationStatus(jobId, 'COMPLETE', {
      audio_key: audioKey,
      tempo_bpm: cppResponse.tempoBpm,
      scale_type: cppResponse.scaleType,
    });
  }
}
```

### cpp-core Integration

**Endpoint:** `POST http://cpp-core:8080/generate`

**Request:**
```json
{
  "image_data": "<base64-encoded-image>",
  "genre_override": "HOUSE",
  "mode": "model"
}
```

**Response:**
```json
{
  "midi_path": "/tmp/composition.mid",
  "tempo_bpm": 120,
  "scale_type": "minor"
}
```

### audio-producer Integration

**Endpoint:** `POST http://audio-producer:9001/render`

**Request:**
```json
{
  "midi_path": "/tmp/composition.mid",
  "output_path": "/tmp/output.wav"
}
```

**Response:**
```json
{
  "audio_path": "/tmp/output.wav",
  "status": "success"
}
```

---

## B5. AWS Deployment Architecture

### Components

```
                        Internet
                           │
                           ▼
                    [CloudFront CDN]
                           │
                ┌──────────┴──────────┐
                │                     │
         [Frontend S3]          [ALB (HTTPS)]
                                      │
                               [Gateway ECS]
                                      │
        ┌─────────────────────────────┼────────────────────┐
        │                             │                    │
   [cpp-core ECS]           [audio-producer ECS]      [ml ECS]
        │                             │                    │
        └─────────────────────────────┴────────────────────┘
                                      │
                     ┌────────────────┴────────────────┐
                     │                                 │
              [RDS MySQL]                      [S3 Uploads]
```

### ECS Services

| Service | Port | Public | Description |
|---------|------|--------|-------------|
| gateway | 4000 | Yes (ALB) | GraphQL API |
| cpp-core | 8080 | No | C++ composition engine |
| audio-producer | 9001 | No | Python audio renderer |
| ml | 8501 | No | TensorFlow model server |

### Security Groups

**ALB Security Group:**
- Inbound: 443 from 0.0.0.0/0 (internet)
- Outbound: 4000 to Gateway ECS

**Gateway ECS Security Group:**
- Inbound: 4000 from ALB SG
- Outbound: 
  - 8080 to cpp-core
  - 9001 to audio-producer
  - 8501 to ml
  - 3306 to RDS
  - 443 to S3 (via VPC endpoint)

**Internal Services SG:**
- Inbound: 8080/9001/8501 from Gateway SG
- Outbound: All (for S3/RDS)

**RDS Security Group:**
- Inbound: 3306 from Gateway SG

---

## B6. Environment Variables

### Gateway Service

```bash
# AWS
AWS_REGION=us-east-2
AWS_ACCESS_KEY_ID=<from-IAM-role-or-ssm>
AWS_SECRET_ACCESS_KEY=<from-secrets-manager>
S3_BUCKET_NAME=soundcanvas-uploads
USE_S3=true

# Database
RDS_ENDPOINT=soundcanvas-db.xxxx.us-east-2.rds.amazonaws.com:3306
RDS_USERNAME=admin
RDS_PASSWORD=<from-secrets-manager>
RDS_DB_NAME=soundcanvas
RDS_SSL=false

# Services
CPP_CORE_URL=http://cpp-core:8080
AUDIO_PRODUCER_URL=http://audio-producer:9001

# Server
PORT=4000
NODE_ENV=production
```

### cpp-core Service

```bash
AUDIO_PRODUCER_URL=http://audio-producer:9001
MODEL_SERVER_URL=http://ml:8501/v1/models/soundcanvas:predict
```

### audio-producer Service

```bash
FREESOUND_API_KEY=<your-freesound-api-key>
```

---

## B7. Deployment Steps

### 1. Build & Push Docker Images

```bash
# Gateway
cd gateway
docker build -t soundcanvas-gateway .
docker tag soundcanvas-gateway:latest <account>.dkr.ecr.us-east-2.amazonaws.com/soundcanvas-gateway:latest
docker push <account>.dkr.ecr.us-east-2.amazonaws.com/soundcanvas-gateway:latest

# cpp-core
cd cpp-core
docker build -t soundcanvas-cpp-core .
docker tag soundcanvas-cpp-core:latest <account>.dkr.ecr.us-east-2.amazonaws.com/soundcanvas-cpp-core:latest
docker push <account>.dkr.ecr.us-east-2.amazonaws.com/soundcanvas-cpp-core:latest

# audio-producer
cd audio-producer
docker build -t soundcanvas-audio-producer .
docker tag soundcanvas-audio-producer:latest <account>.dkr.ecr.us-east-2.amazonaws.com/soundcanvas-audio-producer:latest
docker push <account>.dkr.ecr.us-east-2.amazonaws.com/soundcanvas-audio-producer:latest
```

### 2. Create S3 Buckets

```bash
# Uploads bucket
aws s3 mb s3://soundcanvas-uploads --region us-east-2
aws s3api put-bucket-cors --bucket soundcanvas-uploads --cors-configuration file://s3-cors.json

# Frontend bucket
aws s3 mb s3://soundcanvas-frontend --region us-east-2
aws s3 website s3://soundcanvas-frontend --index-document index.html
```

### 3. Create RDS Instance

```bash
aws rds create-db-instance \
  --db-instance-identifier soundcanvas-db \
  --db-instance-class db.t3.micro \
  --engine mysql \
  --master-username admin \
  --master-user-password <your-password> \
  --allocated-storage 20 \
  --db-name soundcanvas \
  --vpc-security-group-ids sg-xxxxx \
  --db-subnet-group-name soundcanvas-subnet-group \
  --region us-east-2
```

### 4. Deploy ECS Services

```bash
cd infra/terraform
terraform init
terraform plan
terraform apply
```

### 5. Deploy Frontend

```bash
cd frontend
npm run build

# Upload to S3
aws s3 sync .next/static s3://soundcanvas-frontend/static
aws s3 sync .next/standalone s3://soundcanvas-frontend/

# Invalidate CloudFront
aws cloudfront create-invalidation --distribution-id E1234567 --paths "/*"
```

---

## B8. Testing

### Local Development

```bash
# Start local MySQL
docker run -d -p 3306:3306 \
  -e MYSQL_ROOT_PASSWORD=root \
  -e MYSQL_DATABASE=soundcanvas \
  -e MYSQL_USER=soundcanvas \
  -e MYSQL_PASSWORD=soundcanvas \
  mysql:8

# Start gateway
cd gateway
npm install
npm run dev
```

### Test Endpoints

```bash
# Health check
curl http://localhost:4000/graphql \
  -H "Content-Type: application/json" \
  -d '{"query": "query { __typename }"}'

# Create generation
curl http://localhost:4000/graphql \
  -H "Content-Type: application/json" \
  -d '{
    "query": "mutation { createGeneration(input: {genreOverride: \"HOUSE\", mode: \"model\"}) { jobId imageUploadUrl imageId } }"
  }'

# Check status
curl http://localhost:4000/graphql \
  -H "Content-Type: application/json" \
  -d '{
    "query": "query { generationStatus(jobId: \"<job-id>\") { status audioUrl errorMessage } }"
  }'
```

---

## B9. Monitoring & Observability

### CloudWatch Logs

Log groups:
- `/soundcanvas/gateway`
- `/soundcanvas/cpp-core`
- `/soundcanvas/audio-producer`
- `/soundcanvas/ml`

### Metrics to Track

1. **Generation Pipeline:**
   - Total generations per day
   - Average generation time
   - Success/failure rate
   - Status distribution (PENDING/RUNNING/COMPLETE/FAILED)

2. **API Performance:**
   - GraphQL query latency
   - Mutation response times
   - Error rate by resolver

3. **Infrastructure:**
   - ECS task health
   - RDS connection count
   - S3 request count
   - ALB target health

---

## B10. Security Checklist

- [ ] No credentials in Git
- [ ] All secrets in SSM Parameter Store or Secrets Manager
- [ ] S3 buckets block public access (pre-signed URLs only)
- [ ] RDS in private subnets
- [ ] Security groups follow least-privilege
- [ ] ALB has HTTPS listener with valid certificate
- [ ] IAM roles for ECS tasks (not access keys)
- [ ] VPC endpoints for S3 (cost optimization)
- [ ] CloudFront with HTTPS for frontend

---

## Success Criteria ✅

- [x] GraphQL schema implemented
- [x] S3 storage service with pre-signed URLs
- [x] RDS database with migrations
- [x] Orchestrator calling cpp-core and audio-producer
- [x] ECS task definitions ready
- [x] Environment variables documented
- [x] Deployment guide complete

---

## Next Steps

1. **Person A**: Update `.env.local` with production GraphQL endpoint
2. **Person A**: Test end-to-end flow with deployed backend
3. **Both**: Run production smoke tests
4. **Both**: Set up CI/CD for automated deployments

---

## Files Modified/Created

- ✅ `gateway/src/schema.ts` - GraphQL schema
- ✅ `gateway/src/resolvers/Mutation.ts` - Mutations
- ✅ `gateway/src/resolvers/Query.ts` - Queries
- ✅ `gateway/src/services/storage.ts` - S3 service
- ✅ `gateway/src/services/orchestrator.ts` - Pipeline orchestrator
- ✅ `gateway/src/db.ts` - Database functions
- ✅ `gateway/.env.example` - Environment template
- ✅ `infra/terraform/main.tf` - Infrastructure template

**Total Implementation: ~1500 lines of backend code**
