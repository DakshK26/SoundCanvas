#!/bin/sh
# Runs when LocalStack is ready. Makes the same bucket and FIFO queue Terraform creates in AWS.
# VisibilityTimeout=120 must match queue.tf and pipeline.ts.
awslocal s3 mb s3://soundcanvas-local
awslocal s3api put-bucket-cors --bucket soundcanvas-local --cors-configuration \
  '{"CORSRules":[{"AllowedOrigins":["*"],"AllowedMethods":["GET","POST"],"AllowedHeaders":["*"]}]}'
awslocal sqs create-queue --queue-name soundcanvas-jobs.fifo \
  --attributes FifoQueue=true,VisibilityTimeout=120
