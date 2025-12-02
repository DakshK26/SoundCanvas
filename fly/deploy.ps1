Write-Host "SoundCanvas Fly.io Deployment Script"
Write-Host "===================================="

# Ensure fly is in the path (common issue after fresh install)
$flyPath = "$HOME\.fly\bin"
if (Test-Path $flyPath) {
    $env:Path += ";$flyPath"
}

# Check if flyctl is installed
if (-not (Get-Command fly -ErrorAction SilentlyContinue)) {
    Write-Error "Error: flyctl is not installed. Please install it first."
    exit 1
}

# 1. Deploy ML Service
Write-Host "Deploying ML Service..."
Set-Location fly/tf-serving
$mlAppName = "soundcanvas-ml-$(Get-Date -Format 'yyyyMMddHHmmss')"
# Use 'apps create' instead of 'launch' to avoid interactive prompts
fly apps create --name $mlAppName --org personal
# We need to run deploy from the root context to access sibling folders
Set-Location ../..
fly deploy --app $mlAppName --config fly/tf-serving/fly.toml --dockerfile fly/tf-serving/Dockerfile --ha=false

# 2. Deploy Backend Service
Write-Host "Deploying Backend Service..."
# We are already at root
$backendAppName = "soundcanvas-backend-$(Get-Date -Format 'yyyyMMddHHmmss')"
# Use 'apps create' instead of 'launch' to avoid interactive prompts
fly apps create --name $backendAppName --org personal

# Create Volume for Data
fly volumes create soundcanvas_data --region ord --size 3 --app $backendAppName --yes

# Update Secrets & Env Vars
Write-Host "Setting up environment variables..."
fly secrets set AWS_ACCESS_KEY_ID=minioadmin AWS_SECRET_ACCESS_KEY=minioadmin DB_PASSWORD=soundcanvas --app $backendAppName

# Update S3_ENDPOINT to public URL
$publicUrl = "https://$backendAppName.fly.dev"
# Deploy from root context with HA disabled (single node, single volume)
fly deploy --app $backendAppName --config fly/backend/fly.toml --dockerfile fly/backend/Dockerfile --env S3_ENDPOINT="$publicUrl`:9000" --env SC_TF_SERVING_URL="http://$mlAppName.internal:8501/v1/models/soundcanvas:predict" --ha=false

Write-Host "===================================="
Write-Host "Backend Deployed!"
Write-Host "Gateway URL: https://$backendAppName.fly.dev/graphql"
Write-Host "MinIO URL: https://$backendAppName.fly.dev:9000"
Write-Host ""
Write-Host "Next Steps:"
Write-Host "1. Go to Vercel and deploy the 'frontend' folder."
Write-Host "2. Set the Environment Variable in Vercel:"
Write-Host "   NEXT_PUBLIC_GRAPHQL_ENDPOINT=https://$backendAppName.fly.dev/graphql"
Write-Host "===================================="
