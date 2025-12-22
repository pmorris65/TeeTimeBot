# Deployment Guide: Scheduled Lambda with Docker

## Overview
This bot runs on AWS Lambda with Docker, triggered on a schedule via EventBridge (CloudWatch Events).

## Prerequisites
- AWS Account
- AWS CLI configured
- Docker installed locally
- ECR repository created

## Build & Push Docker Image

```bash
# Set variables
AWS_ACCOUNT_ID=your-account-id
AWS_REGION=us-east-1
REPO_NAME=teetimebot

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Build image
docker build -t $REPO_NAME:latest .

# Tag for ECR
docker tag $REPO_NAME:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REPO_NAME:latest

# Push to ECR
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REPO_NAME:latest
```

## Create Lambda Function

```bash
aws lambda create-function \
  --function-name teetimebot-scheduled \
  --role arn:aws:iam::$AWS_ACCOUNT_ID:role/lambda-execution-role \
  --code ImageUri=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REPO_NAME:latest \
  --package-type Image \
  --timeout 60 \
  --memory-size 1024 \
  --environment Variables="{CLUBHOUSE_USERNAME=your_username,CLUBHOUSE_PASSWORD=your_password,CLUBHOUSE_URL=https://cypresslakecc.clubhouseonline-e3.com/Member-Central}" \
  --region $AWS_REGION
```

## Create EventBridge Schedule

```bash
# Schedule to run every Saturday at 6:00 AM UTC
aws events put-rule \
  --name teetimebot-schedule \
  --schedule-expression "cron(0 6 ? * SAT *)" \
  --state ENABLED \
  --region $AWS_REGION

# Add Lambda as target
aws events put-targets \
  --rule teetimebot-schedule \
  --targets "Id=1,Arn=arn:aws:lambda:$AWS_REGION:$AWS_ACCOUNT_ID:function:teetimebot-scheduled,RoleArn=arn:aws:iam::$AWS_ACCOUNT_ID:role/eventbridge-invoke-role" \
  --region $AWS_REGION
```

## IAM Roles Needed

### Lambda Execution Role
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
```

### EventBridge Invoke Role
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "lambda:InvokeFunction",
      "Resource": "arn:aws:lambda:*:*:function:teetimebot-scheduled"
    }
  ]
}
```

## Testing Locally

```bash
# Build and run locally
docker build -t teetimebot:latest .

# Run with environment variables
docker run \
  -e CLUBHOUSE_USERNAME=your_username \
  -e CLUBHOUSE_PASSWORD=your_password \
  teetimebot:latest
```

## Monitor Execution

```bash
# View Lambda logs
aws logs tail /aws/lambda/teetimebot-scheduled --follow

# Check execution history
aws lambda get-function-concurrency --function-name teetimebot-scheduled
```

## Update Function

```bash
# After rebuilding image:
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REPO_NAME:latest

aws lambda update-function-code \
  --function-name teetimebot-scheduled \
  --image-uri $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REPO_NAME:latest \
  --region $AWS_REGION
```

## Notes

- The function timeout is set to 60 seconds; adjust if needed
- Memory is set to 1024 MB for Selenium/Chrome headless; may need higher for complex operations
- The schedule `cron(0 6 ? * SAT *)` runs at 6 AM UTC every Saturday
- Store credentials securely using AWS Secrets Manager instead of environment variables for production
