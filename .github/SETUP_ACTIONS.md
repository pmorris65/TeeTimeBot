# GitHub Actions Setup for ECR Deployment

## Overview
This GitHub Actions workflow automatically builds and pushes a Docker image to ECR whenever you push to the `main` branch, then updates your Lambda function.

## Prerequisites

### 1. Create IAM Role for GitHub Actions (OIDC)

Run this command to create a trust policy for GitHub Actions:

```bash
AWS_ACCOUNT_ID=your-account-id
GITHUB_REPO=pmorris65/TeeTimeBot

aws iam create-role \
  --role-name github-actions-ecr-role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {
          "Federated": "arn:aws:iam::688290476312:oidc-provider/token.actions.githubusercontent.com"
        },
        "Action": "sts:AssumeRoleWithWebIdentity",
        "Condition": {
          "StringEquals": {
            "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
            "token.actions.githubusercontent.com:sub": "repo:pmorris65/TeeTimeBot:ref:refs/heads/main"
          }
        }
      }
    ]
  }'
```

### 2. Attach Permissions Policy

```bash
aws iam put-role-policy \
  --role-name github-actions-ecr-role \
  --policy-name ecr-lambda-policy \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload",
          "ecr:CreateRepository"
        ],
        "Resource": "arn:aws:ecr:*:688290476312:repository/teetimebot"
      },
      {
        "Effect": "Allow",
        "Action": "ecr:GetAuthorizationToken",
        "Resource": "*"
      },
      {
        "Effect": "Allow",
        "Action": [
          "lambda:UpdateFunctionCode",
          "lambda:GetFunction"
        ],
        "Resource": "arn:aws:lambda:*:688290476312:function:teetimebot-scheduled"
      }
    ]
  }'
```

### 3. Add Repository Secret

Add your AWS Account ID as a GitHub secret:

1. Go to your GitHub repo → **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Name: `AWS_ACCOUNT_ID`
4. Value: Your 12-digit AWS account ID

## How It Works

1. **Trigger**: Push to `main` branch
2. **Build**: Builds Docker image locally
3. **Push**: Pushes to ECR with both commit SHA and `latest` tags
4. **Update**: Automatically updates Lambda function with new image
5. **Verify**: Confirms Lambda update completed

## Workflow File Location

`.github/workflows/deploy.yml`

## Customization

**Change AWS region:**
```yaml
AWS_REGION: us-west-2  # Change to your region
```

**Trigger on different branch:**
```yaml
on:
  push:
    branches:
      - main
      - develop  # Add other branches
```

**Change image update strategy:**

Option 1: Only push image, manual Lambda update
```yaml
# Remove the "Update Lambda function" and "Wait for Lambda update" steps
```

Option 2: Update multiple Lambda functions
```yaml
- name: Update Lambda functions
  run: |
    aws lambda update-function-code --function-name teetimebot-scheduled ...
    aws lambda update-function-code --function-name teetimebot-dev ...
```

## Monitoring

**View workflow runs:**
- GitHub repo → **Actions** tab

**Check ECR images:**
```bash
aws ecr describe-images --repository-name teetimebot
```

**View Lambda deployment history:**
```bash
aws lambda get-function --function-name teetimebot-scheduled
```

## Troubleshooting

**Workflow fails with "credentials could not be retrieved":**
- Verify OIDC provider is set up: `aws iam list-open-id-connect-providers`
- Check IAM role trust relationship

**ECR push fails:**
- Verify ECR repository exists: `aws ecr describe-repositories --repository-names teetimebot`
- Check IAM policy includes ECR permissions

**Lambda update fails:**
- Verify function name matches: `aws lambda list-functions`
- Check IAM policy has `lambda:UpdateFunctionCode` permission

## Security Notes

- Uses OIDC (no long-lived AWS credentials stored)
- Role limited to specific branch (`main` only)
- Scoped permissions for ECR and Lambda only
- Consider adding approval steps for production deployments
