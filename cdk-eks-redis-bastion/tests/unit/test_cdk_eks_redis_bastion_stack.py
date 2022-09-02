import aws_cdk as core
import aws_cdk.assertions as assertions

from cdk_eks_redis_bastion.cdk_eks_redis_bastion_stack import CdkEksRedisBastionStack

# example tests. To run these tests, uncomment this file along with the example
# resource in cdk_eks_redis_bastion/cdk_eks_redis_bastion_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = CdkEksRedisBastionStack(app, "cdk-eks-redis-bastion")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
