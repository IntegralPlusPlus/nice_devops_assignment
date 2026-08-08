from aws_cdk import (
    Stack,
    Duration,
    CfnOutput,
    aws_iam as iam,
    DefaultStackSynthesizer
)
from constructs import Construct

class GitHubOidcStack(Stack):
    BOOTSTRAP_QUALIFIER = DefaultStackSynthesizer.DEFAULT_QUALIFIER

    def __init__(self, 
                 scope: Construct, 
                 construct_id: str, 
                 github_repo: str,
                 existing_provider_arn: str | None = None,
                 **kwargs,) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create OIDC provider
        if existing_provider_arn:
            provider = iam.OpenIdConnectProvider.from_open_id_connect_provider_arn(
                self,
                "GitHubOidcProvider",
                existing_provider_arn,
            )
        else:
            cfn_provider = iam.CfnOIDCProvider(
                            self,
                            "GithubOidcProvider",
                            url="https://token.actions.githubusercontent.com",
                            client_id_list=["sts.amazonaws.com"],
            )

            provider = iam.OpenIdConnectProvider.from_open_id_connect_provider_arn(
                self,
                "GitHubOidcProvider",
                cfn_provider.attr_arn
            )

        # OIDC Principal & Trust Policy 
        # Decides who can take this role by looking at the GitHub token:
        # 1. 'aud': Checks that the token is meant for AWS only
        # 2. 'sub': Makes sure the request comes from our exact repository.
        #    The '*' allows all branches (include main). This is our main defense to keep other 
        #    GitHub users out of our AWS account
        principal_policy = iam.OpenIdConnectPrincipal(
            provider,
            conditions={
                "StringEquals": {
                    "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
                },
                "StringLike": {
                    "token.actions.githubusercontent.com:sub": f"repo:{github_repo}:*",
                },
            },
        )

        # Add role for CI pipeline
        deploy_role = iam.Role(
            self,
            "GithubActionsDeployRole",
            role_name="gh-actions-cdk-deploy",
            assumed_by=principal_policy,
            max_session_duration=Duration.hours(1),
            description=f"OIDC deploy role for GitHub repo {github_repo}",
        )

        # Add AssumeRole access for CI pipeline
        deploy_role.add_to_policy(
            iam.PolicyStatement(
                sid="AssumeCdkBootstrapRoles",
                effect=iam.Effect.ALLOW,
                actions=["sts:AssumeRole"],
                resources=[f"arn:aws:iam::{self.account}:role/cdk-{self.BOOTSTRAP_QUALIFIER}-*"],
            )
        )

        # Add access for reading bootstrap role
        # Is neccessary for 'cdk deploy'
        deploy_role.add_to_policy(
            iam.PolicyStatement(
                sid="ReadCdkBootstrapVersion",
                effect=iam.Effect.ALLOW,
                actions=["ssm:GetParameter"],
                resources=[
                    f"arn:aws:ssm:{self.region}:{self.account}:parameter/cdk-bootstrap/{self.BOOTSTRAP_QUALIFIER}/version"
                ],
            )
        )

        CfnOutput(self,
                  "DeployRoleArn",
                  value=deploy_role.role_arn,
                  description="Put this into the GitHub secret AWS_DEPLOY_ROLE_ARN")

        CfnOutput(self, "OidcProviderArn", value=provider.open_id_connect_provider_arn)
