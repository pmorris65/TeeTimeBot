# Serverless Framework GitHub Actions Deployment

## Overview

The `.github/workflows/serverless-deploy.yml` workflow automatically deploys your Lambda function using the Serverless Framework whenever you push to the `main` branch. Serverless handles building the Docker image, pushing to ECR, creating/updating the Lambda function, and setting the EventBridge schedule — all in one command.

## Prerequisites

1. **AWS Account** with appropriate permissions
2. **GitHub Repository** with Secrets configured
3. **OIDC Provider** set up in AWS (for secure credential handoff)
4. **IAM Role** for GitHub Actions with ECR and Lambda permissions

## Setup Steps

### 1. Create OIDC Provider in AWS (One-time Setup)

```bash
# Create the OIDC identity provider for GitHub Actions
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1 \
  2>/dev/null || echo "OIDC provider already exists"
```

### 2. Create IAM Role for GitHub Actions

Replace `AWS_ACCOUNT_ID` and `GITHUB_REPO` with your values:

```bash
AWS_ACCOUNT_ID=123456789012
GITHUB_REPO=pmorris65/MarcosTeeTimeBot

cat > /tmp/trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::${AWS_ACCOUNT_ID}:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
          "token.actions.githubusercontent.com:sub": "repo:${GITHUB_REPO}:ref:refs/heads/main"
        }
      }
    }
  ]
}
EOF

aws iam create-role \
  --role-name github-actions-serverless-role \
  --assume-role-policy-document file:///tmp/trust-policy.json
```

### 3. Attach IAM Permissions Policy

```bash
AWS_ACCOUNT_ID=123456789012

cat > /tmp/permissions-policy.json <<EOF
{
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
        "ecr:DescribeRepositories",
        "ecr:CreateRepository"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "lambda:CreateFunction",
        "lambda:UpdateFunctionCode",
        "lambda:UpdateFunctionConfiguration",
        "lambda:GetFunction",
        "lambda:AddPermission",
        "lambda:RemovePermission"
      ],
      "Resource": "arn:aws:lambda:*:${AWS_ACCOUNT_ID}:function:teetimebot-*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "iam:PassRole",
        "iam:CreateRole",
        "iam:PutRolePolicy",
        "iam:GetRole",
        "iam:DeleteRole",
        "iam:DeleteRolePolicy",
        "iam:AttachRolePolicy",
        "iam:DetachRolePolicy",
        "iam:TagRole"
      ],
      "Resource": "arn:aws:iam::${AWS_ACCOUNT_ID}:role/teetimebot-*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "events:PutRule",
        "events:PutTargets",
        "events:RemoveTargets",
        "events:DeleteRule",
        "events:DescribeRule"
      ],
      "Resource": "arn:aws:events:*:${AWS_ACCOUNT_ID}:rule/teetimebot-*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "cloudformation:CreateStack",
        "cloudformation:UpdateStack",
        "cloudformation:DeleteStack",
        "cloudformation:DescribeStacks",
        "cloudformation:CreateChangeSet",
        "cloudformation:DeleteChangeSet",
        "cloudformation:DescribeChangeSet",
        "cloudformation:ExecuteChangeSet",
        "cloudformation:DescribeStackEvents",
        "cloudformation:DescribeStackResource",
        "cloudformation:DescribeStackResources",
        "cloudformation:ValidateTemplate"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": "sts:GetCallerIdentity",
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:CreateBucket",
        "s3:ListBucket",
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:GetBucketVersioning",
        "s3:PutBucketVersioning",
        "s3:GetBucketLocation",
        "s3:ListBucketVersions",
        "s3:PutBucketTagging",
        "s3:PutBucketPolicy",
        "s3:PutEncryptionConfiguration"
      ],
      "Resource": [
        "arn:aws:s3:::teetimebot-*",
        "arn:aws:s3:::teetimebot-*/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogGroups",
        "logs:DescribeLogStreams",
        "logs:TagResource"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
EOF

aws iam put-role-policy \
  --role-name github-actions-serverless-role \
  --policy-name serverless-deployment-policy \
  --policy-document file:///tmp/permissions-policy.json
```

### 4. Add GitHub Secrets

Go to your GitHub repository **Settings → Secrets and variables → Actions** and add:

| Secret Name | Value | Example |
|-------------|-------|---------|
| `AWS_ACCOUNT_ID` | Your 12-digit AWS account ID | `123456789012` |
| `CLUBHOUSE_USERNAME` | Your Clubhouse username | `your_email@example.com` |
| `CLUBHOUSE_PASSWORD` | Your Clubhouse password | `your_secure_password` |

**Optional:**

| Secret Name | Value | Default |
|-------------|-------|---------|
| `CLUBHOUSE_URL` | Clubhouse online URL | `https://cypresslakecc.clubhouseonline-e3.com/Member-Central` |

### 5. Update Workflow Role ARN

Update `.github/workflows/serverless-deploy.yml` if you used a different IAM role name:

```yaml
# Line 32 in serverless-deploy.yml
role-to-assume: arn:aws:iam::${{ secrets.AWS_ACCOUNT_ID }}:role/github-actions-serverless-role
```

## Deployment Trigger

The workflow runs automatically whenever you:
- Push code to the `main` branch
- Or manually trigger it from the **Actions** tab → select **Deploy with Serverless Framework** → **Run workflow**

## Monitoring Deployment

### View Workflow Logs

1. Go to your GitHub repo → **Actions** tab
2. Click the latest **Deploy with Serverless Framework** workflow run
3. View live logs as deployment progresses

### Check Lambda Function Status

```bash
# View deployed function details
aws lambda get-function \
  --function-name teetimebot-clubhouseBot \
  --region us-east-1 \
  --query 'Configuration.{Name:FunctionName,Status:State,Updated:LastModified,Memory:MemorySize,Timeout:Timeout}' \
  --output table

# View EventBridge schedule
aws events describe-rule \
  --name teetimebot-scheduled-clubhouseBot-dev \
  --region us-east-1 \
  --query '{Name:Name,State:State,ScheduleExpression:ScheduleExpression}' \
  --output table
```

### View Function Logs

```bash
# Tail recent logs
aws logs tail /aws/lambda/teetimebot-clubhouseBot --follow --region us-east-1

# Or search CloudWatch Logs console
# → Log Groups → /aws/lambda/teetimebot-clubhouseBot
```

## Manual Deployment (Local)

If you want to deploy locally without GitHub Actions:

```bash
# 1. Install Serverless Framework (if not already installed)
npm install -g serverless

# 2. Configure AWS credentials
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_REGION=us-east-1

# 3. Set Clubhouse credentials
export CLUBHOUSE_USERNAME=your_username
export CLUBHOUSE_PASSWORD=your_password

# 4. Deploy
cd /Users/patrick/pythonProjects/TeeTimeBot
serverless deploy --region us-east-1
```

## Troubleshooting

### Workflow fails with "credentials could not be retrieved"

**Cause:** OIDC role not properly configured or subject condition mismatch.

**Fix:**
1. Verify OIDC provider exists:
   ```bash
   aws iam list-open-id-connect-providers
   ```
2. Check trust relationship includes correct repo and branch:
   ```bash
   aws iam get-role --role-name github-actions-serverless-role
   ```
3. Ensure subject matches `repo:pmorris65/MarcosTeeTimeBot:ref:refs/heads/main`

### Docker build fails in workflow

**Cause:** Docker daemon not available or image too large.

**Fix:**
- The workflow uses `docker/setup-buildx-action@v3` which provides Docker in the runner.
- Check Docker buildx availability: runner logs should show buildx installation.
- If image is too large (> 10 GB), reduce dependencies or use a slimmer base image.

### ECR repository not created

**Cause:** IAM permissions missing `ecr:CreateRepository`.

**Fix:**
- Ensure `github-actions-serverless-role` has the `ecr:CreateRepository` permission in the policy.
- Verify policy attached to the role.

### Serverless deploy hangs or times out

**Cause:** Docker build taking too long, or GitHub Actions runner CPU/memory constrained.

**Fix:**
- Docker layer caching: Serverless caches layers, but first build takes longer.
- GitHub Actions runners are 2-core machines; builds can take 5-10 minutes.
- Increase runner timeout if needed (default is 6 hours for workflow).

### Lambda function not found after deployment

**Cause:** Serverless creates function with auto-generated name (e.g., `teetimebot-clubhouseBot-dev`).

**Fix:**
- Check actual function name in CloudFormation or AWS console:
  ```bash
  aws lambda list-functions --region us-east-1 | grep teetimebot
  ```
- Update monitoring/testing scripts to use the actual function name.

## Next Steps

- **Secure credentials:** Move `CLUBHOUSE_USERNAME` and `CLUBHOUSE_PASSWORD` to AWS Secrets Manager instead of GitHub Secrets (more secure for production).
- **Add approval gates:** Require manual approval before deploying to production.
- **Multi-environment:** Create separate serverless configurations for `dev`, `staging`, and `prod`.
- **Rollback:** Serverless automatically stores previous deployments; use `serverless rollback` to revert.

## Useful Commands

```bash
# Deploy (runs automatically on push to main)
serverless deploy

# Deploy a single function
serverless deploy function -f clubhouseBot

# View deployment outputs
serverless info

# Rollback to previous version
serverless rollback

# Remove entire stack
serverless remove
```
