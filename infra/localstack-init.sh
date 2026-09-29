#!/bin/sh
# Local copies of the bucket and queue Terraform creates in AWS.
awslocal s3 mb s3://soundcanvas-local
awslocal s3api put-bucket-cors --bucket soundcanvas-local --cors-configuration \
  '{"CORSRules":[{"AllowedOrigins":["*"],"AllowedMethods":["GET","POST"],"AllowedHeaders":["*"]}]}'
awslocal sqs create-queue --queue-name soundcanvas-jobs.fifo \
  --attributes FifoQueue=true,VisibilityTimeout=120
