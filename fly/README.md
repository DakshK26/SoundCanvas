# SoundCanvas Fly.io Deployment

This directory contains the configuration to deploy the SoundCanvas backend to [Fly.io](https://fly.io) and the frontend to [Vercel](https://vercel.com), completely replacing the AWS infrastructure while keeping the code intact.

## Architecture

Instead of AWS services, we use:
- **Fly.io Machines**: Runs the Backend Monolith (Gateway, C++ Core, Audio Producer, Audio Renderer, MySQL, MinIO).
- **Fly.io Volumes**: Persistent storage for MySQL database and MinIO (S3 replacement) files.
- **MinIO**: Replaces AWS S3 for object storage.
- **Local MySQL**: Replaces AWS RDS.
- **Vercel**: Hosts the Next.js Frontend.

## Prerequisites

1. [Fly CLI](https://fly.io/docs/hands-on/install-flyctl/) installed and logged in (`fly auth login`).
2. [Vercel CLI](https://vercel.com/docs/cli) installed (optional, can use UI).

## Deployment Steps

### 1. Deploy Backend to Fly.io

Run the deployment script from the root of the repository:

```bash
chmod +x fly/deploy.sh
./fly/deploy.sh
```

This script will:
1. Create and deploy the ML service (`soundcanvas-ml`).
2. Create and deploy the Backend service (`soundcanvas-backend`).
3. Provision a 3GB persistent volume.
4. Configure environment variables to link everything together.

**Note:** The script generates unique app names (e.g., `soundcanvas-backend-12345`). Note down the **Gateway URL** printed at the end.

### 2. Deploy Frontend to Vercel

1. Go to the Vercel Dashboard and "Add New Project".
2. Import the `SoundCanvas` repository.
3. Set the **Root Directory** to `frontend`.
4. In **Environment Variables**, add:
   - `NEXT_PUBLIC_GRAPHQL_ENDPOINT`: The URL from the previous step (e.g., `https://soundcanvas-backend-12345.fly.dev/graphql`).
5. Click **Deploy**.

## How it Works

- **Monolithic Container**: To support the shared filesystem requirement of the audio pipeline without complex NFS setups, we run `gateway`, `cpp-core`, `audio-producer`, and `audio-renderer` in a single container managed by `supervisord`.
- **MinIO**: We run a local S3-compatible server (MinIO) inside the container. The Gateway is configured to use this instead of AWS S3 via the `S3_ENDPOINT` environment variable.
- **Persistence**: A Fly Volume is mounted at `/data`, ensuring that the Database and MinIO files persist across restarts.

## Troubleshooting

- **Logs**: Use `fly logs -a <app-name>` to see what's happening.
- **MinIO Console**: You can access the MinIO console at `http://<app-url>:9090` (Login: `minioadmin` / `minioadmin`).
