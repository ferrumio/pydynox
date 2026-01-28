"""Integration tests for DynamoDBClient table operations (sync).

Full test coverage using sync_* methods. Async API is validated separately
in test_client_table_async.py with minimal tests.
"""

import pytest
from pydynox import DynamoDBClient
from pydynox.exceptions import (
    ResourceInUseException,
    ResourceNotFoundException,
    ValidationException,
)


@pytest.fixture
def client(dynamodb_endpoint):
    """Create a pydynox client without pre-created table."""
    return DynamoDBClient(
        region="us-east-1",
        endpoint_url=dynamodb_endpoint,
        access_key="testing",
        secret_key="testing",
    )


# ============ Basic Table Operations ============


def test_create_table_hash_key_only(client):
    """Test creating a table with only a hash key."""
    client.sync_create_table("hash_only_table", hash_key=("pk", "S"))

    assert client.sync_table_exists("hash_only_table")
    client.sync_delete_table("hash_only_table")


@pytest.mark.asyncio
async def test_create_table_hash_and_range_key(client):
    """Test creating a table with hash and range key."""
    client.sync_create_table(
        "hash_range_table",
        hash_key=("pk", "S"),
        range_key=("sk", "S"),
    )

    assert client.sync_table_exists("hash_range_table")

    # Verify we can write to it (async)
    await client.put_item("hash_range_table", {"pk": "test", "sk": "item", "data": "value"})
    result = await client.get_item("hash_range_table", {"pk": "test", "sk": "item"})
    assert result is not None
    assert result["data"] == "value"

    client.sync_delete_table("hash_range_table")


@pytest.mark.parametrize(
    "key_type",
    [
        pytest.param("S", id="string"),
        pytest.param("N", id="number"),
    ],
)
def test_create_table_different_key_types(client, key_type):
    """Test creating tables with different key types."""
    table_name = f"key_type_{key_type}_table"

    client.sync_create_table(table_name, hash_key=("pk", key_type))
    assert client.sync_table_exists(table_name)
    client.sync_delete_table(table_name)


def test_create_table_provisioned_billing(client):
    """Test creating a table with provisioned capacity."""
    client.sync_create_table(
        "provisioned_table",
        hash_key=("pk", "S"),
        billing_mode="PROVISIONED",
        read_capacity=10,
        write_capacity=5,
    )

    assert client.sync_table_exists("provisioned_table")
    client.sync_delete_table("provisioned_table")


@pytest.mark.asyncio
async def test_create_table_with_wait(client):
    """Test creating a table and waiting for it to be active."""
    client.sync_create_table("wait_table", hash_key=("pk", "S"), wait=True)

    # Table should be immediately usable (async)
    await client.put_item("wait_table", {"pk": "test", "data": "value"})
    result = await client.get_item("wait_table", {"pk": "test"})
    assert result is not None
    assert result["data"] == "value"

    client.sync_delete_table("wait_table")


def test_table_exists_returns_false_for_nonexistent(client):
    """Test that sync_table_exists returns False for non-existent tables."""
    assert client.sync_table_exists("nonexistent_table_12345") is False


def test_delete_table(client):
    """Test deleting a table."""
    client.sync_create_table("to_delete_table", hash_key=("pk", "S"))
    assert client.sync_table_exists("to_delete_table")

    client.sync_delete_table("to_delete_table")

    assert client.sync_table_exists("to_delete_table") is False


def test_wait_for_table_active(client):
    """Test waiting for a table to become active."""
    client.sync_create_table("wait_active_table", hash_key=("pk", "S"))
    client.sync_wait_for_table_active("wait_active_table")

    # Table should be usable (sync)
    client.sync_put_item("wait_active_table", {"pk": "test"})

    client.sync_delete_table("wait_active_table")


# ============ Error Cases ============


def test_delete_nonexistent_table_raises_error(client):
    """Test that deleting a non-existent table raises ResourceNotFoundException."""
    with pytest.raises(ResourceNotFoundException):
        client.sync_delete_table("nonexistent_table_12345")


def test_create_duplicate_table_raises_error(client):
    """Test that creating a duplicate table raises ResourceInUseException."""
    client.sync_create_table("duplicate_table", hash_key=("pk", "S"))

    with pytest.raises(ResourceInUseException):
        client.sync_create_table("duplicate_table", hash_key=("pk", "S"))

    client.sync_delete_table("duplicate_table")


def test_create_table_invalid_key_type_raises_error(client):
    """Test that invalid key type raises ValidationException."""
    with pytest.raises(ValidationException):
        client.sync_create_table("invalid_table", hash_key=("pk", "INVALID"))


def test_create_table_invalid_billing_mode_raises_error(client):
    """Test that invalid billing mode raises ValidationException."""
    with pytest.raises(ValidationException):
        client.sync_create_table(
            "invalid_billing_table",
            hash_key=("pk", "S"),
            billing_mode="INVALID",
        )


# ============ GSI Tests ============


def test_create_table_with_gsi_hash_only(client):
    """Test creating a table with a GSI that has only a hash key."""
    client.sync_create_table(
        "gsi_hash_table",
        hash_key=("pk", "S"),
        range_key=("sk", "S"),
        global_secondary_indexes=[
            {
                "index_name": "email-index",
                "hash_key": ("email", "S"),
                "projection": "ALL",
            }
        ],
    )

    assert client.sync_table_exists("gsi_hash_table")

    # Verify we can write (sync)
    client.sync_put_item(
        "gsi_hash_table", {"pk": "USER#1", "sk": "PROFILE", "email": "test@example.com"}
    )

    client.sync_delete_table("gsi_hash_table")


def test_create_table_with_gsi_hash_and_range(client):
    """Test creating a table with a GSI that has hash and range keys."""
    client.sync_create_table(
        "gsi_range_table",
        hash_key=("pk", "S"),
        range_key=("sk", "S"),
        global_secondary_indexes=[
            {
                "index_name": "status-index",
                "hash_key": ("status", "S"),
                "range_key": ("created_at", "S"),
                "projection": "ALL",
            }
        ],
    )

    assert client.sync_table_exists("gsi_range_table")
    client.sync_delete_table("gsi_range_table")


def test_create_table_with_multiple_gsis(client):
    """Test creating a table with multiple GSIs."""
    client.sync_create_table(
        "multi_gsi_table",
        hash_key=("pk", "S"),
        range_key=("sk", "S"),
        global_secondary_indexes=[
            {
                "index_name": "email-index",
                "hash_key": ("email", "S"),
                "projection": "ALL",
            },
            {
                "index_name": "status-index",
                "hash_key": ("status", "S"),
                "range_key": ("pk", "S"),
                "projection": "KEYS_ONLY",
            },
        ],
    )

    assert client.sync_table_exists("multi_gsi_table")
    client.sync_delete_table("multi_gsi_table")


def test_create_table_with_gsi_keys_only_projection(client):
    """Test creating a table with a GSI using KEYS_ONLY projection."""
    client.sync_create_table(
        "gsi_keys_only_table",
        hash_key=("pk", "S"),
        global_secondary_indexes=[
            {
                "index_name": "type-index",
                "hash_key": ("type", "S"),
                "projection": "KEYS_ONLY",
            }
        ],
    )

    assert client.sync_table_exists("gsi_keys_only_table")
    client.sync_delete_table("gsi_keys_only_table")


# ============ LSI Tests ============


def test_create_table_with_lsi(client):
    """Create a table with a Local Secondary Index."""
    client.sync_create_table(
        "lsi_table",
        hash_key=("pk", "S"),
        range_key=("sk", "S"),
        local_secondary_indexes=[
            {
                "index_name": "status-index",
                "range_key": ("status", "S"),
                "projection": "ALL",
            }
        ],
    )

    assert client.sync_table_exists("lsi_table")

    # Verify we can write (sync)
    client.sync_put_item(
        "lsi_table",
        {"pk": "USER#1", "sk": "PROFILE#1", "status": "active"},
    )

    client.sync_delete_table("lsi_table")


def test_create_table_with_lsi_keys_only_projection(client):
    """Create a table with LSI using KEYS_ONLY projection."""
    client.sync_create_table(
        "lsi_keys_only_table",
        hash_key=("pk", "S"),
        range_key=("sk", "S"),
        local_secondary_indexes=[
            {
                "index_name": "age-index",
                "range_key": ("age", "N"),
                "projection": "KEYS_ONLY",
            }
        ],
    )

    assert client.sync_table_exists("lsi_keys_only_table")
    client.sync_delete_table("lsi_keys_only_table")


def test_create_table_with_lsi_include_projection(client):
    """Create a table with LSI using INCLUDE projection."""
    client.sync_create_table(
        "lsi_include_table",
        hash_key=("pk", "S"),
        range_key=("sk", "S"),
        local_secondary_indexes=[
            {
                "index_name": "status-index",
                "range_key": ("status", "S"),
                "projection": "INCLUDE",
                "non_key_attributes": ["email", "name"],
            }
        ],
    )

    assert client.sync_table_exists("lsi_include_table")
    client.sync_delete_table("lsi_include_table")


def test_create_table_with_multiple_lsis(client):
    """Create a table with multiple Local Secondary Indexes."""
    client.sync_create_table(
        "multi_lsi_table",
        hash_key=("pk", "S"),
        range_key=("sk", "S"),
        local_secondary_indexes=[
            {
                "index_name": "status-index",
                "range_key": ("status", "S"),
                "projection": "ALL",
            },
            {
                "index_name": "age-index",
                "range_key": ("age", "N"),
                "projection": "KEYS_ONLY",
            },
        ],
    )

    assert client.sync_table_exists("multi_lsi_table")
    client.sync_delete_table("multi_lsi_table")


def test_create_table_with_gsi_and_lsi(client):
    """Create a table with both GSI and LSI."""
    client.sync_create_table(
        "gsi_lsi_table",
        hash_key=("pk", "S"),
        range_key=("sk", "S"),
        global_secondary_indexes=[
            {
                "index_name": "email-index",
                "hash_key": ("email", "S"),
                "projection": "ALL",
            }
        ],
        local_secondary_indexes=[
            {
                "index_name": "status-index",
                "range_key": ("status", "S"),
                "projection": "ALL",
            }
        ],
    )

    assert client.sync_table_exists("gsi_lsi_table")

    # Verify we can write (sync)
    client.sync_put_item(
        "gsi_lsi_table",
        {
            "pk": "USER#1",
            "sk": "PROFILE",
            "email": "test@example.com",
            "status": "active",
        },
    )

    client.sync_delete_table("gsi_lsi_table")
