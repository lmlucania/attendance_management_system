from diagrams import Cluster, Diagram, Edge
from diagrams.onprem.client import User
from diagrams.onprem.container import Docker
from diagrams.onprem.database import PostgreSQL
from diagrams.onprem.network import Gunicorn, Nginx
from diagrams.programming.framework import Django
from diagrams.programming.language import Python

with Diagram("web_service", show=False):
    user = User("User")

    with Cluster("Host"):
        Docker()

        with Cluster("Container: web"):
            nginx = Nginx("Reverse Proxy")

        with Cluster("Container: app"):
            python = Python()
            django = Django()
            gunicorn = Gunicorn()

        with Cluster("Container: postgres"):
            postgres = PostgreSQL()

    user >> Edge(label="80:80") >> nginx >> Edge(label="8000:8000") >> django >> Edge(label="5433:5432") >> postgres
