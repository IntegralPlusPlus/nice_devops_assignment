from aws_cdk import (
    Stack,
    RemovalPolicy,
    CfnOutput,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy
)
from constructs import Construct

class NiceAssignmentStack(Stack):
    # Serverless stack: S3 bucket + Lambda lister + SNS email notifications

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
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
        
        CfnOutput(self, "BucketName", value=bucket.bucket_name)