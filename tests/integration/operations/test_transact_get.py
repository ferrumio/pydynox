"""Integration tests for transact_get operation.

Tests atomic read of multiple items.
"""

import pytest
from pydynox import Transaction


def test_transact_get_multiple_items(dynamo):
    """Test reading multiple items atomically."""
    # GIVEN multiple items exist
    dynamo.put_item("test_table", {"pk": "TGET#1", "sk": "ITEM#1", "name": "Alice"})
    dynamo.put_item("test_table", {"pk": "TGET#1", "sk": "ITEM#2", "name": "Bob"})
    dynamo.put_item("test_table", {"pk": "TGET#1", "sk": "ITEM#3", "name": "Charlie"})

    # WHEN we read them in a transaction (sync)
    gets = [
        {"table": "test_table", "key": {"pk": "TGET#1", "sk": "ITEM#1"}},
        {"table": "test_table", "key": {"pk": "TGET#1", "sk": "ITEM#2"}},
        {"table": "test_table", "key": {"pk": "TGET#1", "sk": "ITEM#3"}},
    ]
    results = dynamo.sync_transact_get(gets)

    # THEN all items are returned
    assert len(results) == 3
    assert results[0]["name"] == "Alice"
    assert results[1]["name"] == "Bob"
    assert results[2]["name"] == "Charlie"


def test_transact_get_with_missing_item(dynamo):
    """Test transact_get returns None for missing items."""
    # GIVEN one item exists
    dynamo.put_item("test_table", {"pk": "TGET#2", "sk": "EXISTS", "name": "Found"})

    # WHEN we read existing and non-existing items
    gets = [
        {"table": "test_table", "key": {"pk": "TGET#2", "sk": "EXISTS"}},
        {"table": "test_table", "key": {"pk": "TGET#2", "sk": "MISSING"}},
    ]
    results = dynamo.sync_transact_get(gets)

    # THEN existing item is returned, missing is None
    assert len(results) == 2
    assert results[0]["name"] == "Found"
    assert results[1] is None


def test_transact_get_empty_list(dynamo):
    """Test transact_get with empty list returns empty list."""
    results = dynamo.sync_transact_get([])
    assert results == []


def test_transact_get_with_projection(dynamo):
    """Test transact_get with projection expression."""
    # GIVEN an item with multiple attributes
    dynamo.put_item(
        "test_table",
        {"pk": "TGET#3", "sk": "PROJ", "name": "Alice", "age": 30, "email": "a@b.com"},
    )

    # WHEN we read with projection
    gets = [
        {
            "table": "test_table",
            "key": {"pk": "TGET#3", "sk": "PROJ"},
            "projection_expression": "#n, #a",
            "expression_attribute_names": {"#n": "name", "#a": "age"},
        },
    ]
    results = dynamo.sync_transact_get(gets)

    # THEN only projected attributes are returned (plus keys)
    assert len(results) == 1
    assert results[0]["name"] == "Alice"
    assert results[0]["age"] == 30
    # email should not be in result (or might be depending on DynamoDB behavior)


# ========== ASYNC TESTS ==========


@pytest.mark.asyncio
async def test_transact_write_async(dynamo):
    """Test async transact_write (default)."""
    operations = [
        {
            "type": "put",
            "table": "test_table",
            "item": {"pk": "ASYNC_TXN#1", "sk": "ITEM#1", "name": "Alice"},
        },
        {
            "type": "put",
            "table": "test_table",
            "item": {"pk": "ASYNC_TXN#1", "sk": "ITEM#2", "name": "Bob"},
        },
    ]

    # WHEN we execute async transaction (default, no prefix)
    await dynamo.transact_write(operations)

    # THEN items are saved
    result = dynamo.get_item("test_table", {"pk": "ASYNC_TXN#1", "sk": "ITEM#1"})
    assert result is not None
    assert result["name"] == "Alice"


@pytest.mark.asyncio
async def test_transact_get_async(dynamo):
    """Test async transact_get (default)."""
    # GIVEN items exist
    dynamo.put_item("test_table", {"pk": "ASYNC_TGET#1", "sk": "ITEM#1", "name": "Alice"})
    dynamo.put_item("test_table", {"pk": "ASYNC_TGET#1", "sk": "ITEM#2", "name": "Bob"})

    # WHEN we read them async (default, no prefix)
    gets = [
        {"table": "test_table", "key": {"pk": "ASYNC_TGET#1", "sk": "ITEM#1"}},
        {"table": "test_table", "key": {"pk": "ASYNC_TGET#1", "sk": "ITEM#2"}},
    ]
    results = await dynamo.transact_get(gets)

    # THEN all items are returned
    assert len(results) == 2
    assert results[0]["name"] == "Alice"
    assert results[1]["name"] == "Bob"


@pytest.mark.asyncio
async def test_transaction_context_manager_async(dynamo):
    """Test Transaction (async) context manager."""
    # WHEN we use the async context manager
    async with Transaction(dynamo) as txn:
        txn.put("test_table", {"pk": "ASYNC_CTX#1", "sk": "ITEM#1", "name": "Alice"})
        txn.put("test_table", {"pk": "ASYNC_CTX#1", "sk": "ITEM#2", "name": "Bob"})

    # THEN items are saved
    result = dynamo.get_item("test_table", {"pk": "ASYNC_CTX#1", "sk": "ITEM#1"})
    assert result is not None
    assert result["name"] == "Alice"


@pytest.mark.asyncio
async def test_transaction_rollback_on_exception_async(dynamo):
    """Test Transaction (async) does not commit on exception."""
    # GIVEN an existing item
    dynamo.put_item("test_table", {"pk": "ASYNC_CTX#2", "sk": "ITEM", "value": "original"})

    # WHEN an exception occurs
    try:
        async with Transaction(dynamo) as txn:
            txn.put("test_table", {"pk": "ASYNC_CTX#2", "sk": "ITEM", "value": "updated"})
            raise RuntimeError("Simulated error")
    except RuntimeError:
        pass

    # THEN the put was NOT committed
    result = dynamo.get_item("test_table", {"pk": "ASYNC_CTX#2", "sk": "ITEM"})
    assert result is not None
    assert result["value"] == "original"
