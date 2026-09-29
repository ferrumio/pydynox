"""Sync integration tests for DynamoDBClient table delete wait operations.

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


def test_wait_for_table_deleted(client):
    """Test waiting for a table to be deleted."""
    # First create and delete table
    client.sync_create_table("sync_delete_wait", partition_key=("pk", "S"))
    client.sync_delete_table("sync_delete_wait")
    
    # Wait for deletion
    client.sync_wait_for_table_deleted("sync_delete_wait")


def test_delete_table_with_wait(client):
    """Test delete_table with wait=True."""
    client.sync_create_table("sync_delete_wait_with_param", partition_key=("pk", "S"))
    client.sync_delete_table("sync_delete_wait_with_param", wait=True)


def test_delete_table_with_wait_timeout(client):
    """Test delete_table with wait=True and timeout."""
    client.sync_create_table("sync_delete_wait_timeout", partition_key=("pk", "S"))
    client.sync_delete_table("sync_delete_wait_timeout", wait=True, timeout_seconds=30)