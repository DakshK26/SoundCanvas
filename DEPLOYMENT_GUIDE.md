# SoundCanvas Deployment Guide

This guide explains how to redeploy the SoundCanvas application after making code changes.

## Prerequisites

- AWS CLI configured with credentials
- Docker installed and running
- Vercel CLI installed (`npm i -g vercel`)
- Terraform installed

## Architecture Overview

**Frontend**: Next.js app deployed on Vercel  
**Backend**: Three services on AWS ECS (Fargate)
- `gateway` - GraphQL API (Node.js/TypeScript)
- `cpp-core` - Music composition engine (C++)
- `audio-producer` - Audio rendering service (Python/FluidSynth)

**Infrastructure**: AWS ECS, RDS MySQL, S3, Application Load Balancer

---

## Deployment Process

### 1. Frontend Changes (Next.js)

When you modify code in the `frontend/` directory:

```powershell
cd frontend
vercel --prod
```

That's it! Vercel automatically builds and deploys your changes.

**Note**: If you change environment variables, update them first:
```powershell
vercel env rm VARIABLE_NAME production
vercel env add VARIABLE_NAME production
```

---

### 2. Backend Changes (Gateway Service)

When you modify code in the `gateway/` directory:

#### Step 1: Build the Docker image
```powershell
cd C:\Users\khann\OneDrive\Documents\GitHub\SoundCanvas
docker build -t soundcanvas/gateway gateway/
```

#### Step 2: Tag the image for ECR
```powershell
docker tag soundcanvas/gateway:latest 749669712860.dkr.ecr.us-east-2.amazonaws.com/soundcanvas/gateway:latest
```

#### Step 3: Login to ECR
```powershell
aws ecr get-login-password --region us-east-2 | Out-String | docker login --username AWS --password-stdin 749669712860.dkr.ecr.us-east-2.amazonaws.com
```

#### Step 4: Push to ECR
```powershell
docker push 749669712860.dkr.ecr.us-east-2.amazonaws.com/soundcanvas/gateway:latest
```

#### Step 5: Force new deployment
```powershell
aws ecs update-service --cluster soundcanvas-cluster --service soundcanvas-gateway-service --force-new-deployment --region us-east-2
```

#### Step 6: Wait for deployment (optional)
```powershell
aws ecs wait services-stable --cluster soundcanvas-cluster --services soundcanvas-gateway-service --region us-east-2
```

---

### 3. C++ Core Service Changes

When you modify code in the `cpp-core/` directory:

#### Step 1: Build the Docker image
```powershell
cd C:\Users\khann\OneDrive\Documents\GitHub\SoundCanvas
docker build -t soundcanvas/cpp-core cpp-core/
```

#### Step 2: Tag the image for ECR
```powershell
docker tag soundcanvas/cpp-core:latest 749669712860.dkr.ecr.us-east-2.amazonaws.com/soundcanvas/cpp-core:latest
```

#### Step 3: Login to ECR (if not already logged in)
```powershell
aws ecr get-login-password --region us-east-2 | Out-String | docker login --username AWS --password-stdin 749669712860.dkr.ecr.us-east-2.amazonaws.com
```

#### Step 4: Push to ECR
```powershell
docker push 749669712860.dkr.ecr.us-east-2.amazonaws.com/soundcanvas/cpp-core:latest
```

#### Step 5: Force new deployment
```powershell
aws ecs update-service --cluster soundcanvas-cluster --service soundcanvas-cpp-core-service --force-new-deployment --region us-east-2
```

#### Step 6: Wait for deployment (optional)
```powershell
aws ecs wait services-stable --cluster soundcanvas-cluster --services soundcanvas-cpp-core-service --region us-east-2
```

---

### 4. Audio Producer Service Changes

When you modify code in the `audio-producer/` directory:

#### Step 1: Build the Docker image
```powershell
cd C:\Users\khann\OneDrive\Documents\GitHub\SoundCanvas
docker build -t soundcanvas/audio-producer audio-producer/
```

#### Step 2: Tag the image for ECR
```powershell
docker tag soundcanvas/audio-producer:latest 749669712860.dkr.ecr.us-east-2.amazonaws.com/soundcanvas/audio-producer:latest
```

#### Step 3: Login to ECR (if not already logged in)
```powershell
aws ecr get-login-password --region us-east-2 | Out-String | docker login --username AWS --password-stdin 749669712860.dkr.ecr.us-east-2.amazonaws.com
```

#### Step 4: Push to ECR
```powershell
docker push 749669712860.dkr.ecr.us-east-2.amazonaws.com/soundcanvas/audio-producer:latest
```

#### Step 5: Force new deployment
```powershell
aws ecs update-service --cluster soundcanvas-cluster --service soundcanvas-audio-producer-service --force-new-deployment --region us-east-2
```

#### Step 6: Wait for deployment (optional)
```powershell
aws ecs wait services-stable --cluster soundcanvas-cluster --services soundcanvas-audio-producer-service --region us-east-2
```

---

### 5. Infrastructure Changes (Terraform)

When you modify infrastructure configuration in `infra/terraform/`:

#### Step 1: Navigate to terraform directory
```powershell
cd c:\Users\khann\OneDrive\Documents\GitHub\SoundCanvas\infra\terraform
```

#### Step 2: Plan changes
```powershell
terraform plan
```

Review the changes carefully before applying.

#### Step 3: Apply changes
```powershell
terraform apply -auto-approve
```

Or without auto-approve to review:
```powershell
terraform apply
```

---

## Quick Reference Commands

### Check service status
```powershell
aws ecs describe-services --cluster soundcanvas-cluster --services soundcanvas-gateway-service soundcanvas-cpp-core-service soundcanvas-audio-producer-service --region us-east-2 --query 'services[*].{Name:serviceName,Status:status,Running:runningCount,Desired:desiredCount}' --output table
```

### View service logs
```powershell
# Gateway logs
aws logs tail /ecs/soundcanvas/gateway --region us-east-2 --follow

# C++ Core logs
aws logs tail /ecs/soundcanvas/cpp-core --region us-east-2 --follow

# Audio Producer logs
aws logs tail /ecs/soundcanvas/audio-producer --region us-east-2 --follow
```

### Test GraphQL endpoint
```powershell
curl http://soundcanvas-alb-1666421202.us-east-2.elb.amazonaws.com/graphql -Method POST -Body '{"query":"{__typename}"}' -ContentType "application/json"
```

### List running tasks
```powershell
aws ecs list-tasks --cluster soundcanvas-cluster --region us-east-2
```

### Check Vercel deployments
```powershell
cd frontend
vercel ls
```

---

## Deployment Script (All Backend Services)

If you've changed multiple backend services, you can use this script to redeploy everything:

```powershell
# Save this as redeploy-backend.ps1
$ErrorActionPreference = "Stop"

# ECR Login
Write-Host "Logging into ECR..." -ForegroundColor Cyan
aws ecr get-login-password --region us-east-2 | Out-String | docker login --username AWS --password-stdin 749669712860.dkr.ecr.us-east-2.amazonaws.com

# Gateway
Write-Host "`nBuilding Gateway..." -ForegroundColor Cyan
docker build -t soundcanvas/gateway gateway/
docker tag soundcanvas/gateway:latest 749669712860.dkr.ecr.us-east-2.amazonaws.com/soundcanvas/gateway:latest
docker push 749669712860.dkr.ecr.us-east-2.amazonaws.com/soundcanvas/gateway:latest

# CPP Core
Write-Host "`nBuilding CPP Core..." -ForegroundColor Cyan
docker build -t soundcanvas/cpp-core cpp-core/
docker tag soundcanvas/cpp-core:latest 749669712860.dkr.ecr.us-east-2.amazonaws.com/soundcanvas/cpp-core:latest
docker push 749669712860.dkr.ecr.us-east-2.amazonaws.com/soundcanvas/cpp-core:latest

# Audio Producer
Write-Host "`nBuilding Audio Producer..." -ForegroundColor Cyan
docker build -t soundcanvas/audio-producer audio-producer/
docker tag soundcanvas/audio-producer:latest 749669712860.dkr.ecr.us-east-2.amazonaws.com/soundcanvas/audio-producer:latest
docker push 749669712860.dkr.ecr.us-east-2.amazonaws.com/soundcanvas/audio-producer:latest

# Force deployments
Write-Host "`nForcing ECS deployments..." -ForegroundColor Cyan
aws ecs update-service --cluster soundcanvas-cluster --service soundcanvas-gateway-service --force-new-deployment --region us-east-2
aws ecs update-service --cluster soundcanvas-cluster --service soundcanvas-cpp-core-service --force-new-deployment --region us-east-2
aws ecs update-service --cluster soundcanvas-cluster --service soundcanvas-audio-producer-service --force-new-deployment --region us-east-2

Write-Host "`nDeployment initiated! Services will restart with new images." -ForegroundColor Green
Write-Host "Check status with: aws ecs describe-services --cluster soundcanvas-cluster --services soundcanvas-gateway-service soundcanvas-cpp-core-service soundcanvas-audio-producer-service --region us-east-2 --query 'services[*].{Name:serviceName,Running:runningCount}' --output table" -ForegroundColor Yellow
```

Run it from the project root:
```powershell
cd C:\Users\khann\OneDrive\Documents\GitHub\SoundCanvas
.\redeploy-backend.ps1
```

---

## Current Endpoints

- **Frontend**: https://frontend-qbitsjq5r-daksh-khannas-projects.vercel.app
- **GraphQL API**: http://soundcanvas-alb-1666421202.us-east-2.elb.amazonaws.com/graphql
- **RDS Database**: soundcanvas-db.cvguemyy844c.us-east-2.rds.amazonaws.com
- **S3 Bucket**: soundcanvas-uploads-dk

---

## Troubleshooting

### Service won't start
1. Check logs: `aws logs tail /ecs/soundcanvas/[service-name] --region us-east-2 --follow`
2. Check task definition is using latest image
3. Verify security groups allow communication
4. Check RDS security group allows ECS tasks (sg-0dbe3e6c0a9459fa8)

### Image build fails
1. Make sure Docker is running
2. Check Dockerfile syntax
3. Ensure all dependencies are available

### Deployment takes too long
1. Old tasks may take time to drain
2. Check deployment settings in ECS (deployment_maximum_percent, deployment_minimum_healthy_percent)

### Frontend can't connect to backend
1. Verify `NEXT_PUBLIC_GRAPHQL_ENDPOINT` is set correctly in Vercel
2. Check CORS settings in gateway service
3. Test GraphQL endpoint directly with curl

---

## Notes

- **ECR Images**: Always use `:latest` tag for simplicity
- **Credentials**: Never commit `terraform.tfvars`, `aws_credentials.txt`, or any files with secrets
- **Cost**: ECS Fargate charges by vCPU/memory per second. Stop services when not in use to save costs
- **Database**: RDS is publicly accessible but secured by security groups
- **Logs**: CloudWatch logs are retained for 7 days (configurable in terraform)
