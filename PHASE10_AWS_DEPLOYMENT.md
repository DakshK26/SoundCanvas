# Phase 10 - AWS Deployment Guide

Complete step-by-step guide for deploying SoundCanvas to AWS.

---

## Prerequisites

- AWS Account with Admin access
- AWS CLI configured (`aws configure`)
- Docker installed
- Terraform installed (v1.0+)
- Domain name (optional, for custom domain)

---

## Quick Start

```bash
# 1. Clone and navigate
cd SoundCanvas

# 2. Set up environment
cp gateway/.env.example gateway/.env
# Edit gateway/.env with your AWS credentials

# 3. Build Docker images
./scripts/build_all_images.sh

# 4. Deploy infrastructure
cd infra/terraform
terraform init
terraform apply

# 5. Deploy frontend
cd ../../frontend
npm run build
aws s3 sync .next/static s3://soundcanvas-frontend/static
```

---

## Step 1: AWS Account Setup

### 1.1 Create IAM User

```bash
aws iam create-user --user-name soundcanvas-deployer

aws iam attach-user-policy \
  --user-name soundcanvas-deployer \
  --policy-arn arn:aws:iam::aws:policy/AdministratorAccess

aws iam create-access-key --user-name soundcanvas-deployer
```

Save the Access Key ID and Secret Access Key.

### 1.2 Configure AWS CLI

```bash
aws configure
# AWS Access Key ID: <your-key>
# AWS Secret Access Key: <your-secret>
# Default region name: us-east-2
# Default output format: json
```

---

## Step 2: Create S3 Buckets

### 2.1 Uploads Bucket

```bash
# Create bucket
aws s3 mb s3://soundcanvas-uploads-prod --region us-east-2

# Block public access
aws s3api put-public-access-block \
  --bucket soundcanvas-uploads-prod \
  --public-access-block-configuration \
    "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

# Add CORS configuration
cat > s3-cors.json <<EOF
{
  "CORSRules": [
    {
      "AllowedOrigins": ["https://soundcanvas.yourdomain.com", "http://localhost:3000"],
      "AllowedMethods": ["GET", "PUT", "HEAD"],
      "AllowedHeaders": ["*"],
      "ExposeHeaders": ["ETag"],
      "MaxAgeSeconds": 3000
    }
  ]
}
EOF

aws s3api put-bucket-cors \
  --bucket soundcanvas-uploads-prod \
  --cors-configuration file://s3-cors.json
```

### 2.2 Frontend Bucket

```bash
# Create bucket
aws s3 mb s3://soundcanvas-frontend-prod --region us-east-2

# Configure as static website
aws s3 website s3://soundcanvas-frontend-prod \
  --index-document index.html \
  --error-document 404.html

# Set bucket policy for public read
cat > s3-frontend-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::soundcanvas-frontend-prod/*"
    }
  ]
}
EOF

aws s3api put-bucket-policy \
  --bucket soundcanvas-frontend-prod \
  --policy file://s3-frontend-policy.json
```

---

## Step 3: Create ECR Repositories

```bash
# Gateway
aws ecr create-repository \
  --repository-name soundcanvas/gateway \
  --region us-east-2

# cpp-core
aws ecr create-repository \
  --repository-name soundcanvas/cpp-core \
  --region us-east-2

# audio-producer
aws ecr create-repository \
  --repository-name soundcanvas/audio-producer \
  --region us-east-2

# ml
aws ecr create-repository \
  --repository-name soundcanvas/ml \
  --region us-east-2
```

---

## Step 4: Build and Push Docker Images

### 4.1 Login to ECR

```bash
aws ecr get-login-password --region us-east-2 | \
  docker login --username AWS --password-stdin \
  <account-id>.dkr.ecr.us-east-2.amazonaws.com
```

### 4.2 Build and Push Gateway

```bash
cd gateway

docker build -t soundcanvas/gateway .

docker tag soundcanvas/gateway:latest \
  <account-id>.dkr.ecr.us-east-2.amazonaws.com/soundcanvas/gateway:latest

docker push <account-id>.dkr.ecr.us-east-2.amazonaws.com/soundcanvas/gateway:latest
```

### 4.3 Build and Push cpp-core

```bash
cd ../cpp-core

docker build -t soundcanvas/cpp-core .

docker tag soundcanvas/cpp-core:latest \
  <account-id>.dkr.ecr.us-east-2.amazonaws.com/soundcanvas/cpp-core:latest

docker push <account-id>.dkr.ecr.us-east-2.amazonaws.com/soundcanvas/cpp-core:latest
```

### 4.4 Build and Push audio-producer

```bash
cd ../audio-producer

docker build -t soundcanvas/audio-producer .

docker tag soundcanvas/audio-producer:latest \
  <account-id>.dkr.ecr.us-east-2.amazonaws.com/soundcanvas/audio-producer:latest

docker push <account-id>.dkr.ecr.us-east-2.amazonaws.com/soundcanvas/audio-producer:latest
```

---

## Step 5: Create RDS MySQL Database

### 5.1 Create DB Subnet Group

```bash
aws rds create-db-subnet-group \
  --db-subnet-group-name soundcanvas-db-subnet \
  --db-subnet-group-description "SoundCanvas DB Subnets" \
  --subnet-ids subnet-xxxxx subnet-yyyyy \
  --region us-east-2
```

### 5.2 Create Security Group

```bash
aws ec2 create-security-group \
  --group-name soundcanvas-rds-sg \
  --description "SoundCanvas RDS Security Group" \
  --vpc-id vpc-xxxxx \
  --region us-east-2

# Allow inbound from ECS tasks
aws ec2 authorize-security-group-ingress \
  --group-id sg-xxxxx \
  --protocol tcp \
  --port 3306 \
  --source-group sg-yyyyy \
  --region us-east-2
```

### 5.3 Create RDS Instance

```bash
aws rds create-db-instance \
  --db-instance-identifier soundcanvas-prod \
  --db-instance-class db.t3.micro \
  --engine mysql \
  --engine-version 8.0 \
  --master-username admin \
  --master-user-password '<your-secure-password>' \
  --allocated-storage 20 \
  --db-name soundcanvas \
  --vpc-security-group-ids sg-xxxxx \
  --db-subnet-group-name soundcanvas-db-subnet \
  --backup-retention-period 7 \
  --publicly-accessible false \
  --region us-east-2

# Wait for creation
aws rds wait db-instance-available \
  --db-instance-identifier soundcanvas-prod \
  --region us-east-2

# Get endpoint
aws rds describe-db-instances \
  --db-instance-identifier soundcanvas-prod \
  --query 'DBInstances[0].Endpoint.Address' \
  --output text \
  --region us-east-2
```

---

## Step 6: Store Secrets in AWS Secrets Manager

```bash
# RDS password
aws secretsmanager create-secret \
  --name soundcanvas/rds-password \
  --secret-string '<your-rds-password>' \
  --region us-east-2

# Freesound API key
aws secretsmanager create-secret \
  --name soundcanvas/freesound-api-key \
  --secret-string '<your-freesound-key>' \
  --region us-east-2

# AWS credentials (for S3 access from ECS)
aws secretsmanager create-secret \
  --name soundcanvas/aws-credentials \
  --secret-string '{"access_key":"<key>","secret_key":"<secret>"}' \
  --region us-east-2
```

---

## Step 7: Deploy with Terraform (Full Infrastructure)

### 7.1 Update Terraform Variables

```bash
cd infra/terraform

cat > terraform.tfvars <<EOF
aws_region = "us-east-2"
environment = "prod"
app_name = "soundcanvas"

db_password = "<your-rds-password>"

ecr_gateway_uri = "<account-id>.dkr.ecr.us-east-2.amazonaws.com/soundcanvas/gateway:latest"
ecr_cpp_core_uri = "<account-id>.dkr.ecr.us-east-2.amazonaws.com/soundcanvas/cpp-core:latest"
ecr_audio_producer_uri = "<account-id>.dkr.ecr.us-east-2.amazonaws.com/soundcanvas/audio-producer:latest"

s3_uploads_bucket = "soundcanvas-uploads-prod"
s3_frontend_bucket = "soundcanvas-frontend-prod"

rds_endpoint = "soundcanvas-prod.xxxxx.us-east-2.rds.amazonaws.com:3306"
EOF
```

### 7.2 Initialize and Apply

```bash
terraform init
terraform plan
terraform apply
```

This will create:
- VPC with public/private subnets
- Application Load Balancer
- ECS Cluster and Services
- CloudWatch Log Groups
- IAM Roles and Policies
- Security Groups

---

## Step 8: Deploy Frontend to S3/CloudFront

### 8.1 Build Frontend

```bash
cd ../../frontend

# Update GraphQL endpoint
cat > .env.production.local <<EOF
NEXT_PUBLIC_GRAPHQL_ENDPOINT=https://api.soundcanvas.yourdomain.com/graphql
EOF

npm run build
```

### 8.2 Upload to S3

```bash
# Sync build output
aws s3 sync out/ s3://soundcanvas-frontend-prod/ --delete

# Or for Next.js standalone
aws s3 sync .next/static s3://soundcanvas-frontend-prod/static/
aws s3 sync .next/standalone s3://soundcanvas-frontend-prod/
```

### 8.3 Create CloudFront Distribution

```bash
aws cloudfront create-distribution \
  --origin-domain-name soundcanvas-frontend-prod.s3.us-east-2.amazonaws.com \
  --default-root-object index.html
```

---

## Step 9: Configure Domain and SSL

### 9.1 Request SSL Certificate

```bash
aws acm request-certificate \
  --domain-name soundcanvas.yourdomain.com \
  --subject-alternative-names "*.soundcanvas.yourdomain.com" \
  --validation-method DNS \
  --region us-east-1  # CloudFront requires us-east-1
```

### 9.2 Add DNS Records

Add CNAME records to validate the certificate, then:

```bash
# Point API subdomain to ALB
api.soundcanvas.yourdomain.com -> soundcanvas-alb-xxxxx.us-east-2.elb.amazonaws.com

# Point www to CloudFront
www.soundcanvas.yourdomain.com -> d1234567.cloudfront.net
```

---

## Step 10: Verify Deployment

### 10.1 Test API

```bash
curl https://api.soundcanvas.yourdomain.com/graphql \
  -H "Content-Type: application/json" \
  -d '{"query": "query { __typename }"}'
```

### 10.2 Test Frontend

Open browser: `https://www.soundcanvas.yourdomain.com`

### 10.3 End-to-End Test

1. Upload an image
2. Click "Generate"
3. Wait for completion
4. Play audio
5. Check history

---

## Step 11: Set Up Monitoring

### 11.1 Enable CloudWatch Logs

Already configured in ECS task definitions.

View logs:
```bash
aws logs tail /soundcanvas/gateway --follow
aws logs tail /soundcanvas/cpp-core --follow
aws logs tail /soundcanvas/audio-producer --follow
```

### 11.2 Create CloudWatch Alarms

```bash
# High error rate
aws cloudwatch put-metric-alarm \
  --alarm-name soundcanvas-high-error-rate \
  --alarm-description "Alert when error rate exceeds 5%" \
  --metric-name 5XXError \
  --namespace AWS/ApplicationELB \
  --statistic Average \
  --period 300 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2

# High CPU
aws cloudwatch put-metric-alarm \
  --alarm-name soundcanvas-high-cpu \
  --alarm-description "Alert when ECS CPU exceeds 80%" \
  --metric-name CPUUtilization \
  --namespace AWS/ECS \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2
```

---

## Troubleshooting

### Gateway Can't Connect to RDS

```bash
# Check security group rules
aws ec2 describe-security-groups --group-ids sg-xxxxx

# Test from ECS task
aws ecs execute-command \
  --cluster soundcanvas-cluster \
  --task <task-id> \
  --container gateway \
  --command "mysql -h <rds-endpoint> -u admin -p"
```

### Images Not Uploading to S3

```bash
# Check CORS configuration
aws s3api get-bucket-cors --bucket soundcanvas-uploads-prod

# Check pre-signed URL generation
# Verify AWS credentials in ECS task
```

### Frontend Can't Reach GraphQL API

```bash
# Check ALB target health
aws elbv2 describe-target-health \
  --target-group-arn <target-group-arn>

# Check CORS headers in gateway
curl -I https://api.soundcanvas.yourdomain.com/graphql \
  -H "Origin: https://www.soundcanvas.yourdomain.com"
```

---

## Cost Optimization

Estimated monthly costs (us-east-2):

| Service | Configuration | Cost |
|---------|--------------|------|
| RDS MySQL | db.t3.micro | ~$15 |
| ECS Fargate | 4 tasks, 0.5vCPU each | ~$30 |
| ALB | 1 load balancer | ~$16 |
| S3 | 100GB storage, 10k requests | ~$3 |
| CloudFront | 100GB transfer | ~$10 |
| **Total** | | **~$74/month** |

To reduce costs:
- Use RDS Reserved Instance (~40% discount)
- Use Fargate Spot (~70% discount)
- Set up Auto Scaling to scale down during low usage

---

## Next Steps

- [ ] Set up CI/CD pipeline (GitHub Actions)
- [ ] Configure auto-scaling
- [ ] Add API rate limiting
- [ ] Set up error tracking (Sentry)
- [ ] Configure backup and disaster recovery
- [ ] Add custom domain SSL
- [ ] Set up monitoring dashboards

---

## References

- [AWS ECS Documentation](https://docs.aws.amazon.com/ecs/)
- [RDS MySQL Guide](https://docs.aws.amazon.com/rds/)
- [S3 Pre-signed URLs](https://docs.aws.amazon.com/AmazonS3/latest/userguide/PresignedUrlUploadObject.html)
- [CloudFront Setup](https://docs.aws.amazon.com/cloudfront/)
