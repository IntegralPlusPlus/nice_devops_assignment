import pytest
import aws_cdk as cdk
from aws_cdk.assertions import Match, Template

from nice_assignment.nice_assignment_stack import NiceAssignmentStack

FUNCTION_NAME = "s3_lister"
ROLE_NAME = "lister-lambda-role"

@pytest.fixture(scope="module")
def template() -> Template:
    app = cdk.App()
    stack = NiceAssignmentStack(
        app, "Test",
        notification_email="test@test.bgu.ac.il",
        env=cdk.Environment(account="123456789012", region="eu-central-1")
    )
    
    return Template.from_stack(stack)

def test_s3_bucket_is_private_and_encrypted(template):
    template.has_resource_properties("AWS::S3::Bucket", {
        "PublicAccessBlockConfiguration": {
            "BlockPublicAcls": True, "BlockPublicPolicy": True,
            "IgnorePublicAcls": True, "RestrictPublicBuckets": True,
        },
        "BucketEncryption": Match.any_value(),
    })

def test_s3_bucket_is_one(template):
    template.resource_count_is("AWS::S3::Bucket", 1)

def test_sns_topic_is_one(template):
    template.resource_count_is("AWS::SNS::Topic", 1)

def test_lambda_function_config(template):
    template.has_resource_properties("AWS::Lambda::Function", {
        "FunctionName": FUNCTION_NAME,
        "Handler": "index.handler",
        "Runtime": "python3.13",
        "Environment": {"Variables": Match.exact({
            "BUCKET_NAME": Match.any_value(),
            "TOPIC_ARN": Match.any_value(),
            "LOG_LEVEL": "INFO",
        })}  
    })

def test_lambda_uses_our_explicit_role(template):
    (fn,) = template.find_resources("AWS::Lambda::Function",
                                {"Properties": {"FunctionName": FUNCTION_NAME}}).values()
    (role_id,) = template.find_resources("AWS::IAM::Role",
                                {"Properties": {"RoleName": ROLE_NAME}})

    assert fn["Properties"]["Role"] == {"Fn::GetAtt": [role_id, "Arn"]}

def role_statements(template):
    (role_id,) = template.find_resources("AWS::IAM::Role", {"Properties": {"RoleName": ROLE_NAME}})

    statements = []
    for policy in template.find_resources("AWS::IAM::Policy").values():
        if role_id in [r["Ref"] for r in policy["Properties"]["Roles"]]:
            statements += policy["Properties"]["PolicyDocument"]["Statement"]

    return statements

def as_list(value):
    return value if isinstance(value, list) else [value]

def test_lambda_role_actions(template):
    statements = role_statements(template)
    actions = set()

    for statement in statements:
        if "Action" in statement:
            action = statement["Action"]
            if statement["Effect"] == "Allow":
                actions.update(as_list(action))

    assert actions == {"s3:ListBucket", "sns:Publish", "logs:CreateLogStream", "logs:PutLogEvents"}   

def test_no_statement_targets_all_resources(template):
    for statement in role_statements(template):
        resource = statement["Resource"]
        assert "*" not in as_list(resource), statement.get("Sid")