from aws_cdk import (
    Stack,
    RemovalPolicy,
    Duration,
    CfnOutput,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
    aws_sns as sns,
    aws_sns_subscriptions as subs,
    aws_ssm as ssm,
    aws_lambda as lambda_,
    aws_iam as iam,
    aws_logs as logs
)
from constructs import Construct

# The path where we save the email in AWS SSM
EMAIL_PARAM_NAME = "/nice-assignment/notification-email"

class NiceAssignmentStack(Stack):
    # Serverless stack: S3 bucket + Lambda lister + SNS email notifications

    def __init__(self, scope: Construct, construct_id: str, notification_email: str | None = None, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create S3 bucket
        bucket = s3.Bucket(self, 
                           "AssignmentBucket",
                           block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
                           encryption=s3.BucketEncryption.S3_MANAGED,
                           removal_policy=RemovalPolicy.DESTROY,
                           enforce_ssl=True,
                           auto_delete_objects=True
        )

        # Deploy files from sample_file/ to the s3 bucket
        s3deploy.BucketDeployment(self, 
                                  "SampleFilesDeployment",
                                  sources=[s3deploy.Source.asset("sample_files")],
                                  destination_key_prefix="sample-data/",
                                  destination_bucket=bucket,
                                  retain_on_delete=False,
                                  prune=True
        )

        # Get the email from the command line (if provided), if not, download the saved email from AWS SSM
        email = notification_email or ssm.StringParameter.value_from_lookup(self, EMAIL_PARAM_NAME)

        # Save the email in AWS SSM securely, this helps us avoid writing real email addresses in the code
        ssm.StringParameter(
            self,
            "NotificationEmailParam",
            parameter_name=EMAIL_PARAM_NAME,
            string_value=email,
            description="Email for the SNS subscription; set on the first deployment",
        )

        # Create SNS topic
        topic = sns.Topic(
            self,
            "NotificationTopic",
            display_name="S3 Notifications",
            topic_name="s3-notifications",
        )

        # Add subscription to SNS topic
        topic.add_subscription(subs.EmailSubscription(email))

        # Name of lambda function
        function_name = "s3_lister"

        # Create log group explicitly to enforce a 1-week retention polic
        log_group = logs.LogGroup(self,
                                  "LambdaLogGroup",
                                  log_group_name=f"/aws/lambda/{function_name}",
                                  removal_policy=RemovalPolicy.DESTROY,
                                  retention=logs.RetentionDays.ONE_WEEK
        )

        # Create Lambda role
        lambda_role = iam.Role(self,
                               "LambdaRole",
                               role_name="lister-lambda-role",
                               assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
                               description="Role for S3 lister Lambda function"
        )

        # Add access to read from S3 bucket
        lambda_role.add_to_policy(
            iam.PolicyStatement(sid="S3ListAndGetAccess",
                                effect=iam.Effect.ALLOW,
                                actions=["s3:ListBucket"],
                                resources=[bucket.bucket_arn, bucket.arn_for_objects("*")]
            )
        )

        # Add access to publish to SNS
        lambda_role.add_to_policy(
            iam.PolicyStatement(sid="SNSPublishAccess",
                                effect=iam.Effect.ALLOW,
                                actions=["sns:Publish"],
                                resources=[topic.topic_arn]
            )
        )

        # Add access to write to CloudWatch Logs to own log_group
        lambda_role.add_to_policy(
            iam.PolicyStatement(sid="CloudWatchLogsAccess",
                                effect=iam.Effect.ALLOW,
                                actions=["logs:CreateLogStream", "logs:PutLogEvents"],
                                resources=[f"{log_group.log_group_arn}:*"]
            )
        )

        # Create lambda function
        lister_fn = lambda_.Function(
            self,
            "ListerFunction",
            function_name=function_name,
            runtime=lambda_.Runtime.PYTHON_3_13,
            handler="index.handler",
            code=lambda_.Code.from_asset("lambda"),
            role=lambda_role,
            log_group=log_group,
            timeout=Duration.seconds(10),
            environment={
                "BUCKET_NAME": bucket.bucket_name,
                "TOPIC_ARN": topic.topic_arn,
                "LOG_LEVEL": "INFO",
            },
        )

        # Output bucket name
        CfnOutput(self, "BucketName", value=bucket.bucket_name, description="S3 bucket")

        # Output sns topic
        CfnOutput(self, "TopicArn", value=topic.topic_arn, description="SNS topic")

        # Output lambda function name
        CfnOutput(self, "LambdaFunctionName", value=lister_fn.function_name)

        # Output lambda function arn
        CfnOutput(self, "LambdaRoleArn", value=lambda_role.role_arn)

        # Output manual invoke command
        CfnOutput(self,
                "ManualInvokeCommand",
                value=(
                    f"aws lambda invoke --function-name {function_name} "
                    ),
        )