#!/usr/bin/env python3
import os

import aws_cdk as cdk

from cdk_eks_bastion_redis.cdk_eks_bastion_redis_stack import CdkEksBastionRedisStack

target_account = os.getenv("CDK_TARGET_ACCOUNT")
target_region = os.getenv("CDK_TARGET_REGION")
target_env = cdk.Environment(account=target_account, region=target_region)

app = cdk.App()
CdkEksBastionRedisStack(app, "CdkEksBastionRedisStack", env=target_env)

app.synth()
 