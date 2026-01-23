#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { TeetimebotStack } from '../lib/teetimebot-stack';

const app = new cdk.App();

// GitHub repository info for OIDC role trust policy
const githubOrg = app.node.tryGetContext('githubOrg') || process.env.GITHUB_ORG;
const githubRepo = app.node.tryGetContext('githubRepo') || process.env.GITHUB_REPO;

if (!githubOrg || !githubRepo) {
  throw new Error('Missing required context: githubOrg and githubRepo. Set via -c or environment variables.');
}

new TeetimebotStack(app, 'TeetimebotStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT || process.env.AWS_ACCOUNT_ID,
    region: process.env.CDK_DEFAULT_REGION || process.env.AWS_REGION || 'us-east-1',
  },
  githubOrg,
  githubRepo,
});
