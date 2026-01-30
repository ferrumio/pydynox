"""Tests for client configuration options."""

import pytest
from pydynox import DynamoDBClient


def test_client_with_timeouts(dynamodb_endpoint):
    """Test client creation with timeout configuration."""
    # WHEN we create a client with timeout settings
    client = DynamoDBClient(
        region="us-east-1",
        endpoint_url=dynamodb_endpoint,
        access_key="testing",
        secret_key="testing",
        connect_timeout=5.0,
        read_timeout=30.0,
    )

    # THEN the client works
    assert client.ping() is True


def test_client_with_max_retries(dynamodb_endpoint):
    """Test client creation with max_retries configuration."""
    client = DynamoDBClient(
        region="us-east-1",
        endpoint_url=dynamodb_endpoint,
        access_key="testing",
        secret_key="testing",
        max_retries=5,
    )

    assert client.ping() is True


def test_client_with_all_config_options(dynamodb_endpoint):
    """Test client creation with all config options."""
    client = DynamoDBClient(
        region="us-east-1",
        endpoint_url=dynamodb_endpoint,
        access_key="testing",
        secret_key="testing",
        connect_timeout=10.0,
        read_timeout=60.0,
        max_retries=3,
    )

    assert client.ping() is True
    assert client.get_region() == "us-east-1"


@pytest.mark.asyncio
async def test_client_operations_with_timeouts(dynamodb_endpoint):
    """Test that operations work with timeout configuration."""
    # GIVEN a client with timeout settings
    client = DynamoDBClient(
        region="us-east-1",
        endpoint_url=dynamodb_endpoint,
        access_key="testing",
        secret_key="testing",
        connect_timeout=5.0,
        read_timeout=30.0,
    )

    # Create table if not exists
    table_name = "test_config_table"
    if not client.sync_table_exists(table_name):
        client.sync_create_table(
            table_name,
            partition_key=("pk", "S"),
            sort_key=("sk", "S"),
            wait=True,
        )

    # WHEN we do put_item and get_item
    await client.put_item(table_name, {"pk": "CONFIG#1", "sk": "TEST", "data": "value"})
    result = await client.get_item(table_name, {"pk": "CONFIG#1", "sk": "TEST"})

    # THEN operations succeed
    assert result is not None
    assert result["data"] == "value"

    # Cleanup
    await client.delete_item(table_name, {"pk": "CONFIG#1", "sk": "TEST"})


@pytest.mark.parametrize(
    "connect_timeout,read_timeout",
    [
        pytest.param(1.0, 5.0, id="short_timeouts"),
        pytest.param(10.0, 60.0, id="long_timeouts"),
        pytest.param(0.5, 1.0, id="very_short_timeouts"),
    ],
)
def test_various_timeout_values(dynamodb_endpoint, connect_timeout, read_timeout):
    """Test client with various timeout values."""
    client = DynamoDBClient(
        region="us-east-1",
        endpoint_url=dynamodb_endpoint,
        access_key="testing",
        secret_key="testing",
        connect_timeout=connect_timeout,
        read_timeout=read_timeout,
    )

    assert client.ping() is True


def test_client_default_region():
    """Test that client uses default region when not specified."""
    # This test doesn't connect, just checks region resolution
    client = DynamoDBClient(
        endpoint_url="http://localhost:8000",
        access_key="testing",
        secret_key="testing",
    )

    # Should default to us-east-1 or env var
    region = client.get_region()
    assert region is not None
    assert len(region) > 0
