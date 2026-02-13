import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as ecr from 'aws-cdk-lib/aws-ecr';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as scheduler from 'aws-cdk-lib/aws-scheduler';
import { Construct } from 'constructs';

interface TeetimebotStackProps extends cdk.StackProps {
  githubOrg: string;
  githubRepo: string;
  stage: 'prod' | 'dev';
}

export class TeetimebotStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: TeetimebotStackProps) {
    super(scope, id, props);

    const { githubOrg, githubRepo, stage } = props;
    const isProd = stage === 'prod';

    // GitHub OIDC role and all IAM policies — only in prod stack
    if (isProd) {
      const githubOidcProvider = iam.OpenIdConnectProvider.fromOpenIdConnectProviderArn(
        this,
        'GitHubOidcProvider',
        `arn:aws:iam::${this.account}:oidc-provider/token.actions.githubusercontent.com`
      );

      const githubActionsRole = new iam.Role(this, 'GitHubActionsRole', {
        roleName: 'github-actions-teetimebot-role',
        assumedBy: new iam.WebIdentityPrincipal(
          githubOidcProvider.openIdConnectProviderArn,
          {
            StringEquals: {
              'token.actions.githubusercontent.com:aud': 'sts.amazonaws.com',
            },
            StringLike: {
              'token.actions.githubusercontent.com:sub': `repo:${githubOrg}/${githubRepo}:*`,
            },
          }
        ),
      });

      // ECR permissions
      githubActionsRole.addToPolicy(new iam.PolicyStatement({
        sid: 'ECRAuth',
        actions: ['ecr:GetAuthorizationToken'],
        resources: ['*'],
      }));

      githubActionsRole.addToPolicy(new iam.PolicyStatement({
        sid: 'ECRPush',
        actions: [
          'ecr:BatchCheckLayerAvailability',
          'ecr:GetDownloadUrlForLayer',
          'ecr:BatchGetImage',
          'ecr:PutImage',
          'ecr:InitiateLayerUpload',
          'ecr:UploadLayerPart',
          'ecr:CompleteLayerUpload',
          'ecr:DescribeRepositories',
          'ecr:DescribeImages',
        ],
        resources: [`arn:aws:ecr:${this.region}:${this.account}:repository/teetimebot`],
      }));

      // CloudFormation permissions for CDK (both stacks)
      githubActionsRole.addToPolicy(new iam.PolicyStatement({
        sid: 'CloudFormation',
        actions: [
          'cloudformation:CreateStack',
          'cloudformation:UpdateStack',
          'cloudformation:DeleteStack',
          'cloudformation:DescribeStacks',
          'cloudformation:DescribeStackEvents',
          'cloudformation:DescribeStackResources',
          'cloudformation:GetTemplate',
          'cloudformation:ValidateTemplate',
          'cloudformation:CreateChangeSet',
          'cloudformation:DescribeChangeSet',
          'cloudformation:ExecuteChangeSet',
          'cloudformation:DeleteChangeSet',
          'cloudformation:GetTemplateSummary',
        ],
        resources: [
          `arn:aws:cloudformation:${this.region}:${this.account}:stack/TeetimebotStack/*`,
          `arn:aws:cloudformation:${this.region}:${this.account}:stack/TeetimebotStack-Dev/*`,
        ],
      }));

      // Lambda permissions
      githubActionsRole.addToPolicy(new iam.PolicyStatement({
        sid: 'Lambda',
        actions: [
          'lambda:CreateFunction',
          'lambda:UpdateFunctionCode',
          'lambda:UpdateFunctionConfiguration',
          'lambda:DeleteFunction',
          'lambda:GetFunction',
          'lambda:GetFunctionConfiguration',
          'lambda:AddPermission',
          'lambda:RemovePermission',
          'lambda:GetPolicy',
          'lambda:TagResource',
          'lambda:UntagResource',
          'lambda:ListTags',
        ],
        resources: [`arn:aws:lambda:${this.region}:${this.account}:function:teetimebot-*`],
      }));

      // EventBridge Scheduler permissions
      githubActionsRole.addToPolicy(new iam.PolicyStatement({
        sid: 'Scheduler',
        actions: [
          'scheduler:CreateSchedule',
          'scheduler:UpdateSchedule',
          'scheduler:DeleteSchedule',
          'scheduler:GetSchedule',
          'scheduler:ListSchedules',
          'scheduler:TagResource',
          'scheduler:UntagResource',
        ],
        resources: [`arn:aws:scheduler:${this.region}:${this.account}:schedule/default/teetimebot-*`],
      }));

      // IAM permissions for Lambda execution role (both stacks)
      githubActionsRole.addToPolicy(new iam.PolicyStatement({
        sid: 'IAMRoles',
        actions: [
          'iam:CreateRole',
          'iam:DeleteRole',
          'iam:GetRole',
          'iam:UpdateRole',
          'iam:PassRole',
          'iam:AttachRolePolicy',
          'iam:DetachRolePolicy',
          'iam:PutRolePolicy',
          'iam:DeleteRolePolicy',
          'iam:GetRolePolicy',
          'iam:ListRolePolicies',
          'iam:ListAttachedRolePolicies',
          'iam:TagRole',
          'iam:UntagRole',
        ],
        resources: [
          `arn:aws:iam::${this.account}:role/TeetimebotStack-*`,
          `arn:aws:iam::${this.account}:role/TeetimebotStack-Dev-*`,
          `arn:aws:iam::${this.account}:role/cdk-*`,
        ],
      }));

      // SSM for CDK bootstrap
      githubActionsRole.addToPolicy(new iam.PolicyStatement({
        sid: 'SSM',
        actions: ['ssm:GetParameter', 'ssm:GetParameters'],
        resources: [`arn:aws:ssm:${this.region}:${this.account}:parameter/cdk-bootstrap/*`],
      }));

      // S3 for CDK staging and video bucket management (both stacks)
      githubActionsRole.addToPolicy(new iam.PolicyStatement({
        sid: 'S3CDKStaging',
        actions: [
          's3:GetObject',
          's3:PutObject',
          's3:DeleteObject',
          's3:ListBucket',
          's3:GetBucketLocation',
          's3:CreateBucket',
          's3:DeleteBucket',
          's3:PutLifecycleConfiguration',
          's3:GetLifecycleConfiguration',
          's3:PutBucketPolicy',
          's3:GetBucketPolicy',
          's3:DeleteBucketPolicy',
        ],
        resources: [
          `arn:aws:s3:::cdk-*-assets-${this.account}-${this.region}`,
          `arn:aws:s3:::cdk-*-assets-${this.account}-${this.region}/*`,
          `arn:aws:s3:::teetimebot-videos-${this.account}`,
          `arn:aws:s3:::teetimebot-videos-${this.account}/*`,
          `arn:aws:s3:::teetimebot-videos-dev-${this.account}`,
          `arn:aws:s3:::teetimebot-videos-dev-${this.account}/*`,
        ],
      }));

      new cdk.CfnOutput(this, 'GitHubActionsRoleArn', {
        value: githubActionsRole.roleArn,
        description: 'GitHub Actions IAM Role ARN',
      });
    }

    // S3 bucket for storing session recording videos
    const bucketName = isProd
      ? `teetimebot-videos-${this.account}`
      : `teetimebot-videos-dev-${this.account}`;

    const videoBucket = new s3.Bucket(this, 'VideoBucket', {
      bucketName,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
      lifecycleRules: [
        { expiration: cdk.Duration.days(30) },
      ],
    });

    // Import existing ECR repository (shared between prod and dev)
    const repository = ecr.Repository.fromRepositoryName(
      this,
      'TeetimebotRepo',
      'teetimebot'
    );

    // Lambda function from container image
    const functionName = isProd ? 'teetimebot-scheduled' : 'teetimebot-dev';
    const imageTag = isProd ? 'latest' : 'dev-latest';

    const fn = new lambda.DockerImageFunction(this, 'TeetimebotFunction', {
      functionName,
      code: lambda.DockerImageCode.fromEcr(repository, { tagOrDigest: imageTag }),
      memorySize: 2048,
      timeout: cdk.Duration.seconds(180),
      environment: {
        CLUBHOUSE_USERNAME: process.env.CLUBHOUSE_USERNAME || '',
        CLUBHOUSE_PASSWORD: process.env.CLUBHOUSE_PASSWORD || '',
        CLUBHOUSE_URL: process.env.CLUBHOUSE_URL || 'https://cypresslakecc.clubhouseonline-e3.com/Member-Central',
        GOOGLE_SHEET_ID: process.env.GOOGLE_SHEET_ID || '',
        GOOGLE_CREDENTIALS: process.env.GOOGLE_CREDENTIALS || '',
        S3_VIDEO_BUCKET: videoBucket.bucketName,
        TEE_TIME_OPEN: process.env.TEE_TIME_OPEN || '06:00',
      },
    });

    // Grant Lambda write access to the video bucket
    videoBucket.grantWrite(fn);

    // EventBridge schedule — prod only (dev is manually invoked)
    if (isProd) {
      const schedulerRole = new iam.Role(this, 'SchedulerRole', {
        assumedBy: new iam.ServicePrincipal('scheduler.amazonaws.com'),
      });
      fn.grantInvoke(schedulerRole);

      new scheduler.CfnSchedule(this, 'WeeklySchedule', {
        name: 'teetimebot-weekly-schedule',
        scheduleExpression: 'cron(59 5 ? * SAT *)',
        scheduleExpressionTimezone: 'America/New_York',
        flexibleTimeWindow: { mode: 'OFF' },
        target: {
          arn: fn.functionArn,
          roleArn: schedulerRole.roleArn,
        },
      });
    }

    // Outputs
    new cdk.CfnOutput(this, 'LambdaFunctionArn', {
      value: fn.functionArn,
      description: `TeeTimeBot Lambda Function ARN (${stage})`,
    });

    new cdk.CfnOutput(this, 'VideoBucketName', {
      value: videoBucket.bucketName,
      description: `S3 bucket for session recording videos (${stage})`,
    });
  }
}
