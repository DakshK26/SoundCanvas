# Vercel Deployment Guide

This guide explains how to deploy the entire SoundCanvas monorepo to Vercel.

## Overview

We have adapted the backend services to run as Vercel Serverless Functions in the `api/` directory.
- **Frontend**: Next.js (Native)
- **Gateway**: Adapted to `api/graphql.ts` (Node.js)
- **ML**: Adapted to `api/predict.py` (Python)
- **Core**: Adapted to `api/compose.py` (Python wrapper)
- **Audio**: Adapted to `api/render.py` (Python wrapper)

## Prerequisites

1.  **Vercel Account**: Create one at [vercel.com](https://vercel.com).
2.  **Vercel CLI**: Install with `npm i -g vercel`.
3.  **Database**: You need a remote MySQL database (e.g., PlanetScale, Aiven, or AWS RDS). Vercel does not host databases.

## Setup Steps

### 1. Environment Variables

Configure the following environment variables in your Vercel Project Settings:

- `DB_HOST`: Your MySQL host
- `DB_USER`: Your MySQL user
- `DB_PASSWORD`: Your MySQL password
- `DB_NAME`: Your MySQL database name
- `SC_TF_SERVING_URL`: Set to `https://<your-vercel-url>/api/predict` (Self-referencing)

### 2. Preparing the ML Model (Optional but Recommended)

The original TensorFlow model is too large for Vercel. You must convert it to TensorFlow Lite (`.tflite`).

1.  Run the conversion script (you may need to write one using `tf.lite.TFLiteConverter`).
2.  Place the `soundcanvas.tflite` file in `ml/models/soundcanvas.tflite`.
3.  The `api/predict.py` function will automatically pick it up.

### 3. Preparing the C++ Core (Advanced)

To run the C++ core on Vercel, you must compile it for **Amazon Linux 2**.

1.  Use Docker to compile:
    ```bash
    docker run -v $(pwd):/src -w /src/cpp-core amazonlinux:2 \
      sh -c "yum install -y cmake3 gcc-c++ make && mkdir build && cd build && cmake3 .. && make"
    ```
2.  Copy the resulting binary to `bin/soundcanvas_core` in the project root.
3.  Commit this binary to the repo (Note: It might be large, consider Git LFS).

### 4. Audio Rendering Limitations

Vercel does not support `fluidsynth` natively. The `api/render.py` endpoint is currently a **mock** that returns a placeholder audio.

**Recommended Solution**:
For a Vercel-only deployment, we recommend moving the audio rendering to the **Frontend** using `soundfont-player` or `midi-player-js`. The backend (`api/compose`) generates the MIDI, and the browser plays it.

## Deployment

1.  Run `vercel` in the root directory.
2.  Follow the prompts.
3.  Vercel will detect the `vercel.json` and deploy the frontend and API functions.

## Troubleshooting

- **Function Size**: If deployment fails due to size, ensure you are using `tflite-runtime` instead of `tensorflow` in `api/requirements.txt`.
- **Timeouts**: Vercel functions have a 10s (Hobby) or 60s (Pro) timeout. Heavy ML/Audio tasks might time out.

