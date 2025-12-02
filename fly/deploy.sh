#!/bin/bash
set -e

echo "SoundCanvas Fly.io Deployment Script"
echo "===================================="

# Check if flyctl is installed
if ! command -v fly &> /dev/null; then
    echo "Error: flyctl is not installed. Please install it first."
    exit 1
fi

# 1. Deploy ML Service
echo "Deploying ML Service..."
cd fly/tf-serving
fly launch --no-deploy --copy-config --name soundcanvas-ml-$(date +%s) --region ord --org personal
fly deploy
ML_APP_NAME=$(fly status --json | jq -r .Name)
cd ../..

# 2. Deploy Backend Service
echo "Deploying Backend Service..."
cd fly/backend
fly launch --no-deploy --copy-config --name soundcanvas-backend-$(date +%s) --region ord --org personal

# Create Volume for Data
APP_NAME=$(fly status --json | jq -r .Name)
fly volumes create soundcanvas_data --region ord --size 3 --app $APP_NAME

# Update Secrets & Env Vars
echo "Setting up environment variables..."
fly secrets set \
    AWS_ACCESS_KEY_ID=minioadmin \
    AWS_SECRET_ACCESS_KEY=minioadmin \
    DB_PASSWORD=soundcanvas \
    --app $APP_NAME

# Update S3_ENDPOINT to public URL (assuming port 9000 is exposed via TCP/HTTP)
# Note: For real SSL on port 9000, you might need dedicated certificates or a separate app.
# For this demo, we'll try to use the fly.dev domain.
PUBLIC_URL="https://$APP_NAME.fly.dev"
fly deploy --env S3_ENDPOINT="${PUBLIC_URL}:9000" --env SC_TF_SERVING_URL="http://$ML_APP_NAME.internal:8501/v1/models/soundcanvas:predict"

echo "===================================="
echo "Backend Deployed!"
echo "Gateway URL: https://$APP_NAME.fly.dev/graphql"
echo "MinIO URL: https://$APP_NAME.fly.dev:9000"
echo ""
echo "Next Steps:"
echo "1. Go to Vercel and deploy the 'frontend' folder."
echo "2. Set the Environment Variable in Vercel:"
echo "   NEXT_PUBLIC_GRAPHQL_ENDPOINT=https://$APP_NAME.fly.dev/graphql"
echo "===================================="
