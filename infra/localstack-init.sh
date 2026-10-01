#!/bin/sh
# Runs when LocalStack is ready (mounted by docker-compose.yml). Makes the same bucket and FIFO
# queue Terraform creates in AWS (storage.tf and queue.tf). awslocal is the aws CLI aimed at LocalStack.
# VisibilityTimeout=120 must match queue.tf and pipeline.ts.

# The bucket, with CORS open to any origin because this is only ever local.
awslocal s3 mb s3://soundcanvas-local
awslocal s3api put-bucket-cors --bucket soundcanvas-local --cors-configuration \
  '{"CORSRules":[{"AllowedOrigins":["*"],"AllowedMethods":["GET","POST"],"AllowedHeaders":["*"]}]}'

# The FIFO job queue. Its URL is SQS_QUEUE_URL in docker-compose.yml.
awslocal sqs create-queue --queue-name soundcanvas-jobs.fifo \
  --attributes FifoQueue=true,VisibilityTimeout=120
