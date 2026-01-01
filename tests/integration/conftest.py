"""Shared fixtures for integration tests.

Uses DynamoDB Local (amazon/dynamodb-local) via testcontainers.
Docker must be running to execute integration tests.
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
    print("\n🐳 Starting DynamoDB Local container...")

    container = DockerContainer("amazon/dynamodb-local:latest")
    container.with_exposed_ports(DYNAMODB_PORT)
    container.with_command("-jar DynamoDBLocal.jar -inMemory -sharedDb")

    container.start()

    # Wait for DynamoDB to be ready
    wait_for_logs(container, "Initializing DynamoDB Local", timeout=30)

    # Give it a moment to fully initialize
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
def _session_client(dynamodb_endpoint):
    """Internal client for session-scoped table creation."""
    return DynamoDBClient(
        region="us-east-1",
        endpoint_url=dynamodb_endpoint,
        access_key="testing",
        secret_key="testing",
    )


@pytest.fixture(scope="session")
def _create_table(_session_client):
    """Create the test table once per session."""
    table_name = "test_table"

    if not _session_client.table_exists(table_name):
        _session_client.create_table(
            table_name,
            hash_key=("pk", "S"),
            range_key=("sk", "S"),
            wait=True,
        )

    return _session_client


@pytest.fixture
def table(_create_table, dynamodb_endpoint):
    """Provide a client with the test table ready.

    Note: Tests should use unique keys to avoid conflicts.
    Use uuid or test-specific prefixes in pk/sk values.
    """
    return DynamoDBClient(
        region="us-east-1",
        endpoint_url=dynamodb_endpoint,
        access_key="testing",
        secret_key="testing",
    )


@pytest.fixture
def dynamo(table):
    """Alias for table fixture - provides a pydynox DynamoDBClient."""
    return table
