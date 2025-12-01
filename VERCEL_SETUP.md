# Vercel Deployment Setup

This project is configured to be deployed on Vercel. While the original architecture uses AWS ECS for heavy compute, this Vercel configuration uses "Serverless Adapters" to run the entire stack in a serverless environment.

## Prerequisites

1.  **Vercel CLI**: Install with `npm i -g vercel`
2.  **Database**: You need a MySQL database accessible from the internet (e.g., PlanetScale, Aiven, or AWS RDS).
3.  **AWS S3**: You still need an S3 bucket for storing images and audio.

## Environment Variables

Set these in your Vercel Project Settings:

```bash
# AWS Credentials (for S3)
AWS_REGION=us-east-2
S3_BUCKET_NAME=your-bucket
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...

# Database
DB_HOST=...
DB_USER=...
DB_PASSWORD=...
DB_NAME=soundcanvas

# Service URLs (Point to Vercel API routes)
# In Vercel, these are relative or full URLs to the same deployment
CPP_SERVICE_URL=https://your-app.vercel.app/api/compose
SC_AUDIO_PRODUCER_URL=https://your-app.vercel.app/api/render
TF_SERVING_URL=https://your-app.vercel.app/api/predict

# Serverless Mode Flag
SERVERLESS_MODE=true
```

## Deployment

Simply run:

```bash
vercel
```

## Architecture Adaptation

To make the microservices work on Vercel:

1.  **Gateway**: Adapted to a Vercel Serverless Function (`api/graphql.ts`).
2.  **ML Service**: Replaced with a Python function (`api/predict.py`) that implements the heuristic mapping logic (removing the heavy TensorFlow dependency for the demo).
3.  **Audio Producer**: Replaced with a Python function (`api/render.py`) that uses `numpy`/`scipy` to synthesize audio algorithmically (removing the FluidSynth dependency).
4.  **C++ Core**: Replaced with a Python mock (`api/compose.py`) that simulates the composition step.

This allows the full "Image -> Audio" pipeline to execute on Vercel's free tier without complex container orchestration.
