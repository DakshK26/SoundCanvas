#!/bin/bash
# Build and push Docker images to AWS ECR
# IMPORTANT: Configure AWS credentials via `aws configure` before running

set -e

echo "=== SoundCanvas Docker Build & Push to ECR ==="
echo ""
echo "Prerequisites:"
echo "  1. AWS CLI configured (run: aws configure)"
echo "  2. Docker running"
echo "  3. ECR repositories created"
echo ""

# Read configuration from aws_credentials.txt (gitignored)
if [ ! -f "aws_credentials.txt" ]; then
    echo "ERROR: aws_credentials.txt not found!"
    echo "Please create this file with your AWS configuration."
    exit 1
fi

# Source credentials
source aws_credentials.txt

# Login to ECR
echo "[1/4] Logging in to AWS ECR..."
aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin \
  $(echo $ECR_GATEWAY_URI | cut -d'/' -f1)

# Build and push Gateway
echo ""
echo "[2/4] Building and pushing Gateway..."
cd gateway
docker build -t soundcanvas/gateway:latest .
docker tag soundcanvas/gateway:latest $ECR_GATEWAY_URI:latest
docker push $ECR_GATEWAY_URI:latest
cd ..

# Build and push cpp-core
echo ""
echo "[3/4] Building and pushing cpp-core..."
cd cpp-core
docker build -t soundcanvas/cpp-core:latest .
docker tag soundcanvas/cpp-core:latest $ECR_CPP_CORE_URI:latest
docker push $ECR_CPP_CORE_URI:latest
cd ..

# Build and push audio-producer
echo ""
echo "[4/4] Building and pushing audio-producer..."
cd audio-producer
docker build -t soundcanvas/audio-producer:latest .
docker tag soundcanvas/audio-producer:latest $ECR_AUDIO_PRODUCER_URI:latest
docker push $ECR_AUDIO_PRODUCER_URI:latest
cd ..

echo ""
echo "✓ All images pushed to ECR successfully!"
echo ""
echo "Next steps:"
echo "  1. cd infra/terraform"
echo "  2. terraform init"
echo "  3. terraform apply"
