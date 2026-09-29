"""Async integration tests for DynamoDBClient table delete wait operations.

Tests the new wait_for_table_deleted functionality.
"""
import pytest
from pydynox import DynamoDBClient


@pytest.fixture
def client(dynamodb_endpoint):
    """Create a pydynox client without pre-created table."""
    return DynamoDBClient(
        region="us-east-1",
        endpoint_url=dynamodb_endpoint,
        access_key="testing",
        secret_key="testing",
    )


@pytest.mark.asyncio
async def test_async_wait_for_table_deleted(client):
    """Test async wait_for_table_deleted."""
    # First create and delete table
    await client.create_table("async_delete_wait", partition_key=("pk", "S"))
    await client.delete_table("async_delete_wait")
    
    # Wait for deletion
    await client.wait_for_table_deleted("async_delete_wait")


@pytest.mark.asyncio
async def test_async_delete_table_with_wait(client):
    """Test async delete_table with wait=True."""
    await client.create_table("async_delete_wait_with_param", partition_key=("pk", "S"))
    await client.delete_table("async_delete_wait_with_param", wait=True)


@pytest.mark.asyncio
async def test_async_delete_table_with_wait_timeout(client):
    """Test async delete_table with wait=True and timeout."""
    await client.create_table("async_delete_wait_timeout", partition_key=("pk", "S"))
    await client.delete_table("async_delete_wait_timeout", wait=True, timeout_seconds=30)