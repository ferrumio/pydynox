"""Async integration tests for DynamoDBClient table operations.

Minimal tests to validate async API works. Full coverage is in test_client_table.py.
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
async def test_async_create_table(client):
    """Test async create_table works."""
    await client.create_table("async_basic", partition_key=("pk", "S"))

    exists = await client.table_exists("async_basic")
    assert exists is True

    await client.delete_table("async_basic")


@pytest.mark.asyncio
async def test_async_table_exists_false(client):
    """Test async table_exists returns False for non-existent."""
    exists = await client.table_exists("nonexistent_async_12345")
    assert exists is False


@pytest.mark.asyncio
async def test_async_create_table_with_wait(client):
    """Test async create_table with wait=True."""
    await client.create_table("async_wait", partition_key=("pk", "S"), wait=True)

    # Table should be usable
    await client.put_item("async_wait", {"pk": "test", "data": "value"})
    result = await client.get_item("async_wait", {"pk": "test"})
    assert result is not None
    assert result["data"] == "value"

    await client.delete_table("async_wait")


@pytest.mark.asyncio
async def test_async_wait_for_table_active(client):
    """Test async wait_for_table_active."""
    await client.create_table("async_wait_active", partition_key=("pk", "S"))
    await client.wait_for_table_active("async_wait_active")

    # Table should be usable
    await client.put_item("async_wait_active", {"pk": "test"})

    await client.delete_table("async_wait_active")


@pytest.mark.asyncio
async def test_async_wait_for_table_deleted(client):
    """Test async wait_for_table_deleted after delete."""
    await client.create_table("async_wait_deleted", partition_key=("pk", "S"), wait=True)
    await client.delete_table("async_wait_deleted")

    await client.wait_for_table_deleted("async_wait_deleted", timeout_seconds=30)

    assert await client.table_exists("async_wait_deleted") is False


@pytest.mark.asyncio
async def test_async_wait_for_table_deleted_already_absent(client):
    """Test async waiter returns at once for a table that does not exist."""
    await client.wait_for_table_deleted("async_never_existed_12345")


@pytest.mark.asyncio
async def test_async_delete_table_with_wait_allows_recreation(client):
    """Test async delete_table(wait=True) lets the same name be created again."""
    await client.create_table("async_recreate", partition_key=("pk", "S"), wait=True)

    await client.delete_table("async_recreate", wait=True, timeout_seconds=30)
    assert await client.table_exists("async_recreate") is False

    await client.create_table("async_recreate", partition_key=("pk", "S"), wait=True)
    assert await client.table_exists("async_recreate") is True

    await client.delete_table("async_recreate")


@pytest.mark.asyncio
async def test_async_create_table_with_gsi(client):
    """Test async create_table with GSI."""
    await client.create_table(
        "async_gsi",
        partition_key=("pk", "S"),
        global_secondary_indexes=[
            {
                "index_name": "email-index",
                "hash_key": ("email", "S"),
                "projection": "ALL",
            }
        ],
    )

    exists = await client.table_exists("async_gsi")
    assert exists is True

    await client.delete_table("async_gsi")
