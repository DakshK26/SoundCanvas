# Build and push Docker images to AWS ECR (PowerShell)
# IMPORTANT: Configure AWS credentials via `aws configure` before running

Write-Host "=== SoundCanvas Docker Build & Push to ECR ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Prerequisites:"
Write-Host "  1. AWS CLI configured (run: aws configure)"
Write-Host "  2. Docker running"
Write-Host "  3. ECR repositories created"
Write-Host ""

# Read configuration from aws_credentials.txt (gitignored)
if (-not (Test-Path "aws_credentials.txt")) {
    Write-Host "ERROR: aws_credentials.txt not found!" -ForegroundColor Red
    Write-Host "Please create this file with your AWS configuration."
    exit 1
}

# Load credentials
Get-Content aws_credentials.txt | ForEach-Object {
    if ($_ -match '^([A-Z_]+)=(.+)$') {
        Set-Variable -Name $matches[1] -Value $matches[2] -Scope Script
    }
}

# Login to ECR
Write-Host "[1/4] Logging in to AWS ECR..." -ForegroundColor Cyan
$ecrDomain = $ECR_GATEWAY_URI -replace '/.*', ''
$password = aws ecr get-login-password --region $AWS_REGION
$password | docker login --username AWS --password-stdin $ecrDomain

# Build and push Gateway
Write-Host "`n[2/4] Building and pushing Gateway..." -ForegroundColor Cyan
Push-Location gateway
docker build -t soundcanvas/gateway:latest .
docker tag soundcanvas/gateway:latest "$ECR_GATEWAY_URI:latest"
docker push "$ECR_GATEWAY_URI:latest"
Pop-Location

# Build and push cpp-core
Write-Host "`n[3/4] Building and pushing cpp-core..." -ForegroundColor Cyan
Push-Location cpp-core
docker build -t soundcanvas/cpp-core:latest .
docker tag soundcanvas/cpp-core:latest "$ECR_CPP_CORE_URI:latest"
docker push "$ECR_CPP_CORE_URI:latest"
Pop-Location

# Build and push audio-producer
Write-Host "`n[4/4] Building and pushing audio-producer..." -ForegroundColor Cyan
Push-Location audio-producer
docker build -t soundcanvas/audio-producer:latest .
docker tag soundcanvas/audio-producer:latest "$ECR_AUDIO_PRODUCER_URI:latest"
docker push "$ECR_AUDIO_PRODUCER_URI:latest"
Pop-Location

Write-Host "`n✓ All images pushed to ECR successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. cd infra\terraform"
Write-Host "  2. terraform init"
Write-Host "  3. terraform apply"
