from unittest import removeHandler
from aws_cdk import (
    # Duration,
    Stack,
    aws_iam as iam,
    aws_ec2 as ec2,
    aws_eks as eks,
    aws_elasticache as elasticache,
    RemovalPolicy as RemovalPolicy
)
from constructs import Construct

class CdkEksBastionRedisStack(Stack): 

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # VPC
        vpc = ec2.Vpc(self, "VPC",
            nat_gateways=1,
            cidr="10.0.0.0/16",
            subnet_configuration=[
                ec2.SubnetConfiguration(name="public",subnet_type=ec2.SubnetType.PUBLIC,cidr_mask=24),
                ec2.SubnetConfiguration(name="application",subnet_type=ec2.SubnetType.PRIVATE_WITH_NAT,cidr_mask=19),
                ec2.SubnetConfiguration(name="redis",subnet_type=ec2.SubnetType.PRIVATE_WITH_NAT,cidr_mask=24),
                ec2.SubnetConfiguration(name="bastion",subnet_type=ec2.SubnetType.PRIVATE_WITH_NAT,cidr_mask=24)
            ],
            
        )
        vpc.apply_removal_policy(RemovalPolicy.DESTROY)
        

        # Security Groups     
        application_sec_group = ec2.SecurityGroup(
            self, "eks_sec_group",security_group_name="application_sec_group", vpc=vpc, allow_all_outbound=True)
            
        application_sec_group.apply_removal_policy(RemovalPolicy.DESTROY)
        
        bastion_sg = ec2.SecurityGroup(
            self, "bastion_sg", vpc=vpc, allow_all_outbound=True, security_group_name="bastion_sg")
        
        bastion_sg.apply_removal_policy(RemovalPolicy.DESTROY)
        
        redis_sec_group = ec2.SecurityGroup(
            self, "redis-sec-groupa",security_group_name="redis-sec-group", vpc=vpc, allow_all_outbound=True)

        redis_sec_group.apply_removal_policy(RemovalPolicy.DESTROY)
                
        redis_sec_group.add_ingress_rule(
            peer=application_sec_group,
            description="Allow Redis connection",
            connection=ec2.Port.tcp(6379),            
        )

        # Subnets
        application_subnet_ids = vpc.select_subnets(subnet_group_name="application").subnet_ids
        redis_subnet_ids = vpc.select_subnets(subnet_group_name="redis").subnet_ids
        public_subnet_ids = vpc.select_subnets(subnet_group_name="public").subnet_ids
        bastion_subnet_ids = vpc.select_subnets(subnet_group_name="bastion").subnet_ids

        # ===== EKS =====
        # Create an admin role
        eks_admin_role = iam.Role(self, 'EKSAdminRole',
            assumed_by=iam.CompositePrincipal(
                iam.AccountPrincipal(account_id=self.account),
                iam.ServicePrincipal(
                    "ec2.amazonaws.com")
            )
        )

        # Create the cluster
        cluster = eks.FargateCluster(self, "MyFargateCluster",
            cluster_name="MyFargateCluster",
            #version=eks.KubernetesVersion.V1_21,
            version=eks.KubernetesVersion.of('1.23'),
            masters_role=eks_admin_role,
            alb_controller=eks.AlbControllerOptions(
                version=eks.AlbControllerVersion.V2_4_1
            ),
            vpc=vpc,
            vpc_subnets=[ec2.SubnetSelection(subnet_group_name="application")],
            endpoint_access= eks.EndpointAccess.PRIVATE
        )

        # Create the Fargate profiles
        cluster.add_fargate_profile(id="flux-fargate-profile",
            fargate_profile_name="flux-fargate-profile",
            selectors=[eks.Selector(namespace='flux')]
        )

        cluster.add_fargate_profile(id="testapp-fargate-profile", 
            fargate_profile_name="testapp-fargate-profile",
            selectors=[eks.Selector(namespace='testapp')]
        )

        # Allow Inbound SG for EKS kubectl
        cluster.kubectl_security_group.add_ingress_rule(bastion_sg, ec2.Port.all_traffic())
        
        # ===== Bastion Host =====
        bastion = ec2.BastionHostLinux(self, "BastionHost",
            vpc=vpc,
            subnet_selection=ec2.SubnetSelection(subnet_group_name="bastion"),
            security_group=bastion_sg,
            init = ec2.CloudFormationInit.from_elements(
                ec2.InitCommand.shell_command('curl -o kubectl https://s3.us-west-2.amazonaws.com/amazon-eks/1.23.7/2022-06-29/bin/linux/amd64/kubectl && chmod +x ./kubectl && mkdir -p $HOME/bin && cp ./kubectl $HOME/bin/kubectl && export PATH=$PATH:$HOME/bin'),
                ec2.InitCommand.shell_command("echo 'export PATH=$PATH:$HOME/bin' >> ~/.bashrc"),
                ec2.InitCommand.shell_command('curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp && sudo mv /tmp/eksctl /usr/local/bin')
            #block_devices=[ec2.BlockDevice(
            #    device_name="EBSBastionHost",
            #    volume=ec2.BlockDeviceVolume.ebs(10,
            #        encrypted=True
            #   )
            #)],           
            )
        )   

        # add EKS policy to Bastion Role
        cluster_admin_policy_statement_json_1 = {
                "Effect": "Allow",
                "Action": [
                    "eks:DescribeCluster"
                ],
                "Resource": "*"
            }
            
        bastion.role.add_to_principal_policy(
            iam.PolicyStatement.from_json(cluster_admin_policy_statement_json_1))

        # Add Bastion role into EKS role
        # TODO: use RBAC
        cluster.aws_auth.add_masters_role(bastion.role)
        

        # ===== ElastiCache for Redis =====         
        redis_subnet_group = elasticache.CfnSubnetGroup(
            scope=self,
            id="redis_subnet_group",
            subnet_ids=redis_subnet_ids, 
            description="subnet group for redis"
        )     

        redis_subnet_group.apply_removal_policy(RemovalPolicy.DESTROY)

        # redis with cluster mode disabled. multi-az replic=2
        redis_cluster_multi_az = elasticache.CfnReplicationGroup(
            self,
            id="redis_cluster_multi_az",
            engine="redis",
            cache_node_type="cache.t3.micro",
            replication_group_description="redis with 2 node cluster mode disabled. multi-az enabled",
            num_cache_clusters=2,
            multi_az_enabled=True,
            automatic_failover_enabled=True,
            cache_subnet_group_name=redis_subnet_group.ref,
            security_group_ids=[redis_sec_group.security_group_id],
        )
        redis_cluster_multi_az.apply_removal_policy(RemovalPolicy.DESTROY) # For testing purpose


        

        