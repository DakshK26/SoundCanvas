#!/bin/sh
# Creates the local copies of what Terraform makes in AWS: the media bucket
# (with browser CORS) and the FIFO job queue.
awslocal s3 mb s3://soundcanvas-local
awslocal s3api put-bucket-cors --bucket soundcanvas-local --cors-configuration \
  '{"CORSRules":[{"AllowedOrigins":["*"],"AllowedMethods":["GET","PUT"],"AllowedHeaders":["*"]}]}'
awslocal sqs create-queue --queue-name soundcanvas-jobs.fifo \
  --attributes FifoQueue=true,VisibilityTimeout=600
