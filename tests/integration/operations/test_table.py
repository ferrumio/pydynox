"""Integration tests for table management operations."""

import pytest
from pydynox import DynamoDBClient
from pydynox.exceptions import (
    TableAlreadyExistsError,
    TableNotFoundError,
    ValidationError,
)


@pytest.fixture
def client(moto_server):
    """Create a pydynox client without pre-created table."""
    return DynamoDBClient(
        region="us-east-1",
        endpoint_url="http://127.0.0.1:5556",
        access_key="testing",
        secret_key="testing",
    )


def test_create_table_with_hash_key_only(client):
    """Test creating a table with only a hash key."""
    client.create_table("hash_only_table", hash_key=("pk", "S"))

    assert client.table_exists("hash_only_table")
    client.delete_table("hash_only_table")


def test_create_table_with_hash_and_range_key(client):
    """Test creating a table with hash and range key."""
    client.create_table(
        "hash_range_table",
        hash_key=("pk", "S"),
        range_key=("sk", "S"),
    )

    assert client.table_exists("hash_range_table")

    # Verify we can write to it
    client.put_item("hash_range_table", {"pk": "test", "sk": "item", "data": "value"})
    result = client.get_item("hash_range_table", {"pk": "test", "sk": "item"})
    assert result["data"] == "value"

    client.delete_table("hash_range_table")


@pytest.mark.parametrize(
    "key_type",
    [
        pytest.param("S", id="string"),
        pytest.param("N", id="number"),
    ],
)
def test_create_table_with_different_key_types(client, key_type):
    """Test creating tables with different key types."""
    table_name = f"key_type_{key_type}_table"

    client.create_table(table_name, hash_key=("pk", key_type))
    assert client.table_exists(table_name)
    client.delete_table(table_name)


def test_create_table_with_provisioned_billing(client):
    """Test creating a table with provisioned capacity."""
    client.create_table(
        "provisioned_table",
        hash_key=("pk", "S"),
        billing_mode="PROVISIONED",
        read_capacity=10,
        write_capacity=5,
    )

    assert client.table_exists("provisioned_table")
    client.delete_table("provisioned_table")


def test_create_table_with_wait(client):
    """Test creating a table and waiting for it to be active."""
    client.create_table("wait_table", hash_key=("pk", "S"), wait=True)

    # Table should be immediately usable
    client.put_item("wait_table", {"pk": "test", "data": "value"})
    result = client.get_item("wait_table", {"pk": "test"})
    assert result["data"] == "value"

    client.delete_table("wait_table")


def test_table_exists_returns_false_for_nonexistent(client):
    """Test that table_exists returns False for non-existent tables."""
    assert client.table_exists("nonexistent_table_12345") is False


def test_delete_table(client):
    """Test deleting a table."""
    client.create_table("to_delete_table", hash_key=("pk", "S"))
    assert client.table_exists("to_delete_table")

    client.delete_table("to_delete_table")
    assert client.table_exists("to_delete_table") is False


def test_delete_nonexistent_table_raises_error(client):
    """Test that deleting a non-existent table raises TableNotFoundError."""
    with pytest.raises(TableNotFoundError):
        client.delete_table("nonexistent_table_12345")


def test_create_duplicate_table_raises_error(client):
    """Test that creating a duplicate table raises TableAlreadyExistsError."""
    client.create_table("duplicate_table", hash_key=("pk", "S"))

    with pytest.raises(TableAlreadyExistsError):
        client.create_table("duplicate_table", hash_key=("pk", "S"))

    client.delete_table("duplicate_table")


def test_create_table_with_invalid_key_type_raises_error(client):
    """Test that invalid key type raises ValidationError."""
    with pytest.raises(ValidationError):
        client.create_table("invalid_table", hash_key=("pk", "INVALID"))


def test_create_table_with_invalid_billing_mode_raises_error(client):
    """Test that invalid billing mode raises ValidationError."""
    with pytest.raises(ValidationError):
        client.create_table(
            "invalid_billing_table",
            hash_key=("pk", "S"),
            billing_mode="INVALID",
        )


def test_wait_for_table_active(client):
    """Test waiting for a table to become active."""
    client.create_table("wait_active_table", hash_key=("pk", "S"))
    client.wait_for_table_active("wait_active_table")

    # Table should be usable
    client.put_item("wait_active_table", {"pk": "test"})

    client.delete_table("wait_active_table")
