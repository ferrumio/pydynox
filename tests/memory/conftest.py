"""Shared fixtures for memory tests.

Uses DynamoDB Local via testcontainers.
"""

import time

import pytest
from pydynox import DynamoDBClient
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs

DYNAMODB_PORT = 8000


@pytest.fixture(scope="session")
def dynamodb_container():
    """Start DynamoDB Local container for the test session."""
    container = DockerContainer("amazon/dynamodb-local:latest")
    container.with_exposed_ports(DYNAMODB_PORT)
    container.with_command("-jar DynamoDBLocal.jar -inMemory -sharedDb")

    container.start()
    wait_for_logs(container, "Initializing DynamoDB Local", timeout=30)
    time.sleep(0.5)

    yield container

    container.stop()


@pytest.fixture(scope="session")
def dynamodb_endpoint(dynamodb_container):
    """Get the DynamoDB Local endpoint URL."""
    host = dynamodb_container.get_container_host_ip()
    port = dynamodb_container.get_exposed_port(DYNAMODB_PORT)
    return f"http://{host}:{port}"


@pytest.fixture(scope="session")
def client(dynamodb_endpoint):
    """Create a DynamoDB client for the session."""
    return DynamoDBClient(
        region="us-east-1",
        endpoint_url=dynamodb_endpoint,
        access_key="testing",
        secret_key="testing",
    )


@pytest.fixture(scope="session")
def memory_table(client):
    """Create a table for memory tests."""
    table_name = "memory_test_table"

    if not client.table_exists(table_name):
        client.create_table(
            table_name,
            hash_key=("pk", "S"),
            range_key=("sk", "S"),
            wait=True,
        )

    return table_name
