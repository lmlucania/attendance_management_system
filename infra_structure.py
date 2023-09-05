from diagrams import Cluster, Diagram, Edge
from diagrams.aws.compute import EC2
from diagrams.aws.network import ELB, InternetGateway, Route53
from diagrams.aws.security import CertificateAuthority
from diagrams.onprem.client import Client
from diagrams.onprem.network import Internet

with Diagram("infra_structure", show=False):
    internet = Internet("Internet")
    client = Client("Client")

    with Cluster("AWS Cloud"):
        route53 = Route53("Route53")

        with Cluster("VPC"):
            igw = InternetGateway("Internet Gateway")

            with Cluster("Public Subnet"):
                CertificateAuthority(height="0.5", width="0.5")
                alb = ELB("ALB")

            with Cluster("Private Subnet"):
                ec2 = EC2("EC2")

    client >> internet >> route53 >> igw >> Edge(label="HTTPS") >> alb >> Edge(label="HTTP") >> ec2
