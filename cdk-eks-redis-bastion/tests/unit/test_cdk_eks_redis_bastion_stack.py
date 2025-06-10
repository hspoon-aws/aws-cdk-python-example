import aws_cdk as core
import aws_cdk.assertions as assertions

from cdk_eks_redis_bastion.cdk_eks_redis_bastion_stack import CdkEksRedisBastionStack

def test_vpc_created():
    app = core.App()
    stack = CdkEksRedisBastionStack(app, "cdk-eks-redis-bastion")
    template = assertions.Template.from_stack(stack)

    # Test that a VPC is created
    template.resource_count_is("AWS::EC2::VPC", 1)
    
    # Test that the required subnets are created
    template.resource_count_is("AWS::EC2::Subnet", 8)  # 4 subnet types * 2 AZs

def test_eks_cluster_created():
    app = core.App()
    stack = CdkEksRedisBastionStack(app, "cdk-eks-redis-bastion")
    template = assertions.Template.from_stack(stack)
    
    # Test that an EKS cluster is created
    template.resource_count_is("AWS::EKS::Cluster", 1)
    
    # Test that the EKS cluster has the correct version
    template.has_resource_properties("AWS::EKS::Cluster", {
        "Version": "1.29"
    })

def test_redis_created():
    app = core.App()
    stack = CdkEksRedisBastionStack(app, "cdk-eks-redis-bastion")
    template = assertions.Template.from_stack(stack)
    
    # Test that a Redis replication group is created
    template.resource_count_is("AWS::ElastiCache::ReplicationGroup", 1)
    
    # Test that the Redis cluster has the correct engine version
    template.has_resource_properties("AWS::ElastiCache::ReplicationGroup", {
        "Engine": "redis",
        "EngineVersion": "7.1"
    })

def test_bastion_host_created():
    app = core.App()
    stack = CdkEksRedisBastionStack(app, "cdk-eks-redis-bastion")
    template = assertions.Template.from_stack(stack)
    
    # Test that a bastion host is created
    template.resource_count_is("AWS::EC2::Instance", 1)
