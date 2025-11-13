# SoundCanvas Phase 10 - Quick Start Guide

**SECURITY:** All credentials are stored in gitignored files. See examples for templates.

## Local Development Setup

### 1. Install Dependencies

```bash
cd gateway
npm install
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your credentials (see aws_credentials.txt)
```

### 3. Run Gateway

```bash
npm run dev
```

Gateway: http://localhost:4000/graphql

### 4. Run Backend Services

```bash
# Terminal 1: cpp-core
cd cpp-core
docker build -t soundcanvas/cpp-core .
docker run -p 8080:8080 soundcanvas/cpp-core

# Terminal 2: audio-producer  
cd audio-producer
docker build -t soundcanvas/audio-producer .
docker run -p 5001:5001 soundcanvas/audio-producer
```

### 5. Run Frontend

```bash
cd frontend
npm install
echo "NEXT_PUBLIC_GRAPHQL_ENDPOINT=http://localhost:4000/graphql" > .env.local
npm run dev
```

Frontend: http://localhost:3000

---

## AWS Deployment

### Prerequisites

1. AWS CLI configured (`aws configure`)
2. Docker installed
3. Terraform installed
4. Created: S3 buckets, RDS instance, ECR repos

### Quick Deploy

```bash
# 1. Configure credentials (see .env.example and terraform.tfvars.example)

# 2. Push Docker images
./scripts/deploy_ecr.sh

# 3. Deploy infrastructure
cd infra/terraform
terraform init
terraform apply

# 4. Get ALB endpoint
terraform output alb_dns_name
```

---

## File Structure

```
gateway/
  .env.example        # Template - copy to .env (gitignored)
  .env                # GITIGNORED - your actual credentials
  
infra/terraform/
  terraform.tfvars.example  # Template - copy to terraform.tfvars
  terraform.tfvars          # GITIGNORED - your actual values
  
aws_credentials.txt   # GITIGNORED - AWS credentials
```

---

## Important Security Notes

✅ **NEVER commit these files:**
- `gateway/.env`
- `infra/terraform/terraform.tfvars`
- `aws_credentials.txt`

✅ **These are safe to commit:**
- `gateway/.env.example`
- `infra/terraform/terraform.tfvars.example`
- All `.example` files

---

## GraphQL API Example

```graphql
# Create generation
mutation {
  createGeneration(input: { genreOverride: "lofi" }) {
    jobId
    imageUploadUrl
  }
}

# Upload image to imageUploadUrl (PUT request)

# Start processing
mutation {
  startGeneration(jobId: "your-job-id") {
    success
  }
}

# Check status
query {
  generationStatus(jobId: "your-job-id") {
    status
    audioUrl
  }
}
```

---

## Troubleshooting

**Connection Refused (Gateway)**
```bash
# Check: .env has correct credentials
# Check: Database is running (local MySQL or RDS)
```

**S3 Access Denied**
```bash
# Check: AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in .env
# Check: IAM user has S3 permissions
```

**Docker Build Fails**
```bash
# Check: Docker is running
# Try: docker system prune
```

---

## Next Steps

- Full deployment guide: `docs/PHASE10_DEPLOYMENT.md`
- GraphQL API docs: `docs/GRAPHQL_API.md`
- Phase summary: `docs/PHASE10_SUMMARY.md`

For support, check CloudWatch logs or RDS connection status.
