#!/usr/bin/env python3
import os

import aws_cdk as cdk

from nice_assignment.nice_assignment_stack import NiceAssignmentStack
from nice_assignment.github_oidc_stack import GitHubOidcStack

APP_STACK_NAME = "NiceAssignmentStack"
LAMBDA_FUNCTION_NAME = "s3_lister"

app = cdk.App()

env = cdk.Environment(account=os.environ["CDK_DEFAULT_ACCOUNT"], 
                      region=os.environ["CDK_DEFAULT_REGION"])

github_repo = app.node.try_get_context("github_repo") or os.environ.get("GITHUB_REPOSITORY")
if github_repo:
    if "/" not in github_repo:
        raise ValueError(f"github_repo must be 'owner/repo', got {github_repo!r}")
    
    GitHubOidcStack(
        app,
        "GitHubOidcStack",
        github_repo=github_repo,
        app_stack_name=APP_STACK_NAME,
        lambda_function_name=LAMBDA_FUNCTION_NAME,
        existing_provider_arn=app.node.try_get_context("existing_oidc_provider_arn"),
        env=env,
        description="One-time CI/CD bootstrap: GitHub OIDC provider and deploy role",
    ) 

# Get notification email
notification_email = app.node.try_get_context("notification_email")

NiceAssignmentStack(app, 
                    "NiceAssignmentStack", 
                    notification_email=notification_email,
                    env=env)

app.synth()
