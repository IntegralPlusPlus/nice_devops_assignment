from aws_cdk import (
    Stack,
    RemovalPolicy,
    CfnOutput,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
    aws_sns as sns,
    aws_sns_subscriptions as subs,
    aws_ssm as ssm
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
                           auto_delete_objects=True)

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

        # Output bucket name
        CfnOutput(self, "BucketName", value=bucket.bucket_name, description="S3 bucket")

        # Output sns topic
        CfnOutput(self, "TopicArn", value=topic.topic_arn, description="SNS topic")