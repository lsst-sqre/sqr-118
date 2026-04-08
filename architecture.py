"""Source for the architecture diagram."""

from diagrams import Cluster, Diagram, Edge
from diagrams.gcp.compute import KubernetesEngine
from diagrams.gcp.database import SQL
from diagrams.k8s.compute import Cronjob, Pod
from diagrams.onprem.database import Influxdb
from diagrams.onprem.client import User, Users
from diagrams.programming.framework import React

graph_attr = {
    "label": "",
    "labelloc": "bbc",
    "nodesep": "0.2",
    "pad": "0.2",
    "ranksep": "0.75",
    "splines": "spline",
}

node_attr = {
    "fontsize": "12.0",
}

with Diagram(
    "Architecture",
    show=False,
    filename="architecture",
    outformat="png",
    graph_attr=graph_attr,
    node_attr=node_attr,
):
    administrator = User("Administrator")
    users = Users("RSP users")

    with Cluster("Phalanx"):
        with Cluster("Services"):
            service_a = KubernetesEngine("Service A")
            service_b = KubernetesEngine("Service B")

        cron = Cronjob("Metrics analysis")
        influxdb = Influxdb("Metrics InfluxDB")

        with Cluster(""):
            semaphore = KubernetesEngine("Semaphore")
            db = SQL("Database")
            semaphore - Edge(constraint="false", minlen="0") - db

        with Cluster("UI"):
            squareone = React("Squareone")
            nublado = Pod("Nublado user pod")
            portal = KubernetesEngine("Portal")

    administrator >> semaphore
    service_a >> semaphore
    service_b >> semaphore
    influxdb >> cron >> semaphore
    semaphore >> squareone >> users
    semaphore >> nublado >> users
    semaphore >> portal >> users

    # Force formatting.
    db - Edge(penwidth="0.0") - users
