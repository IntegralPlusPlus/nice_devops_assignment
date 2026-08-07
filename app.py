#!/usr/bin/env python3
import os

import aws_cdk as cdk

from nice_assignment.nice_assignment_stack import NiceAssignmentStack


app = cdk.App()
env = cdk.Environment(account=os.environ["CDK_DEFAULT_ACCOUNT"], 
                      region=os.environ["CDK_DEFAULT_REGION"])

NiceAssignmentStack(app, "NiceAssignmentStack", env=env)

app.synth()
