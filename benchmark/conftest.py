"""Shared fixtures for benchmarks.

Uses DynamoDB Local (amazon/dynamodb-local) via testcontainers.
"""

import time

import boto3
import pytest
from pydynox import DynamoDBClient
from pynamodb.attributes import NumberAttribute, UnicodeAttribute
from pynamodb.models import Model
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs

DYNAMODB_PORT = 8000


@pytest.fixture(scope="session")
def dynamodb_container():
    """Start DynamoDB Local container for benchmarks."""
    print("\n🐳 Starting DynamoDB Local container...")

    container = DockerContainer("amazon/dynamodb-local:latest")
    container.with_exposed_ports(DYNAMODB_PORT)
    container.with_command("-jar DynamoDBLocal.jar -inMemory -sharedDb")

    container.start()
    wait_for_logs(container, "Initializing DynamoDB Local", timeout=30)
    time.sleep(0.5)

    host = container.get_container_host_ip()
    port = container.get_exposed_port(DYNAMODB_PORT)
    print(f"✅ DynamoDB Local ready at http://{host}:{port}")

    yield container

    print("\n🛑 Stopping DynamoDB Local container...")
    container.stop()


@pytest.fixture(scope="session")
def dynamodb_endpoint(dynamodb_container):
    """Get the DynamoDB Local endpoint URL."""
    host = dynamodb_container.get_container_host_ip()
    port = dynamodb_container.get_exposed_port(DYNAMODB_PORT)
    return f"http://{host}:{port}"


@pytest.fixture(scope="session")
def bench_table(dynamodb_endpoint):
    """Create a DynamoDB table for benchmarks."""
    client = DynamoDBClient(
        region="us-east-1",
        endpoint_url=dynamodb_endpoint,
        access_key="testing",
        secret_key="testing",
    )

    table_name = "bench_table"

    # Delete if exists
    if client.table_exists(table_name):
        client.delete_table(table_name)
        time.sleep(0.5)

    # Create table and wait for it to be active
    client.create_table(
        table_name,
        hash_key=("pk", "S"),
        range_key=("sk", "S"),
        wait=True,
    )

    return client


@pytest.fixture(scope="session")
def pydynox_client(bench_table, dynamodb_endpoint):
    """Create a pydynox DynamoDBClient."""
    return DynamoDBClient(
        region="us-east-1",
        endpoint_url=dynamodb_endpoint,
        access_key="testing",
        secret_key="testing",
    )


@pytest.fixture(scope="session")
def pynamodb_model(bench_table, dynamodb_endpoint):
    """Return the PynamoDB model class configured for the test endpoint."""

    class BenchModel(Model):
        """PynamoDB model for benchmarks."""

        class Meta:
            table_name = "bench_table"
            region = "us-east-1"
            host = dynamodb_endpoint
            aws_access_key_id = "testing"
            aws_secret_access_key = "testing"

        pk = UnicodeAttribute(hash_key=True)
        sk = UnicodeAttribute(range_key=True)
        name = UnicodeAttribute(null=True)
        age = NumberAttribute(null=True)
        email = UnicodeAttribute(null=True)
        status = UnicodeAttribute(null=True)

    # Force PynamoDB to describe the table and cache metadata
    if not BenchModel.exists():
        raise RuntimeError("Table should exist")

    return BenchModel


@pytest.fixture(scope="session")
def boto_client(dynamodb_endpoint):
    """Create a boto3 DynamoDB client for comparison benchmarks."""
    return boto3.client(
        "dynamodb",
        region_name="us-east-1",
        endpoint_url=dynamodb_endpoint,
        aws_access_key_id="testing",
        aws_secret_access_key="testing",
    )
