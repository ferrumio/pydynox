"""Shared fixtures for memory tests.

Uses LocalStack via testcontainers.
"""

import time

import pytest
from pydynox import DynamoDBClient
from testcontainers.localstack import LocalStackContainer


@pytest.fixture(scope="session")
def localstack_container():
    """Start LocalStack container for the test session."""
    container = LocalStackContainer(image="localstack/localstack:latest")
    container.with_services("dynamodb")

    container.start()
    time.sleep(2)

    yield container

    container.stop()


@pytest.fixture(scope="session")
def dynamodb_endpoint(localstack_container):
    """Get the LocalStack endpoint URL."""
    return localstack_container.get_url()


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

    if not client.sync_table_exists(table_name):
        client.sync_create_table(
            table_name,
            partition_key=("pk", "S"),
            sort_key=("sk", "S"),
            wait=True,
        )

    return table_name
