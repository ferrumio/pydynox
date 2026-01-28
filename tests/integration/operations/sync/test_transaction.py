"""Sync integration tests for transaction operations.

Tests sync transaction success and rollback behavior.
"""

import pytest
from pydynox import SyncTransaction
from pydynox.exceptions import PydynoxException, TransactionCanceledException


def test_sync_transact_write_puts_multiple_items(dynamo):
    """Test sync transaction with multiple put operations."""
    # GIVEN multiple items to put
    operations = [
        {
            "type": "put",
            "table": "test_table",
            "item": {"pk": "SYNC_TXN#1", "sk": "ITEM#1", "name": "Alice"},
        },
        {
            "type": "put",
            "table": "test_table",
            "item": {"pk": "SYNC_TXN#1", "sk": "ITEM#2", "name": "Bob"},
        },
        {
            "type": "put",
            "table": "test_table",
            "item": {"pk": "SYNC_TXN#1", "sk": "ITEM#3", "name": "Charlie"},
        },
    ]

    # WHEN we execute the sync transaction
    dynamo.sync_transact_write(operations)

    # THEN all items are saved
    for op in operations:
        item = op["item"]
        key = {"pk": item["pk"], "sk": item["sk"]}
        result = dynamo.sync_get_item("test_table", key)
        assert result is not None
        assert result["name"] == item["name"]


def test_sync_transact_write_with_delete(dynamo):
    """Test sync transaction with put and delete operations."""
    # First, put an item to delete later
    dynamo.sync_put_item("test_table", {"pk": "SYNC_TXN#2", "sk": "DELETE", "name": "ToDelete"})

    operations = [
        {
            "type": "put",
            "table": "test_table",
            "item": {"pk": "SYNC_TXN#2", "sk": "NEW#1", "name": "NewItem"},
        },
        {
            "type": "delete",
            "table": "test_table",
            "key": {"pk": "SYNC_TXN#2", "sk": "DELETE"},
        },
    ]

    dynamo.sync_transact_write(operations)

    # Verify new item exists
    result = dynamo.sync_get_item("test_table", {"pk": "SYNC_TXN#2", "sk": "NEW#1"})
    assert result is not None
    assert result["name"] == "NewItem"

    # Verify deleted item is gone
    result = dynamo.sync_get_item("test_table", {"pk": "SYNC_TXN#2", "sk": "DELETE"})
    assert result is None


def test_sync_transact_write_with_update(dynamo):
    """Test sync transaction with update operation."""
    # First, put an item to update
    dynamo.sync_put_item("test_table", {"pk": "SYNC_TXN#3", "sk": "UPDATE", "counter": 10})

    operations = [
        {
            "type": "update",
            "table": "test_table",
            "key": {"pk": "SYNC_TXN#3", "sk": "UPDATE"},
            "update_expression": "SET #c = #c + :val",
            "expression_attribute_names": {"#c": "counter"},
            "expression_attribute_values": {":val": 5},
        },
    ]

    dynamo.sync_transact_write(operations)

    # Verify update was applied
    result = dynamo.sync_get_item("test_table", {"pk": "SYNC_TXN#3", "sk": "UPDATE"})
    assert result is not None
    assert result["counter"] == 15


def test_sync_transact_write_rollback_on_condition_failure(dynamo):
    """Test that sync transaction rolls back all operations when a condition fails."""
    # GIVEN initial items
    dynamo.sync_put_item("test_table", {"pk": "SYNC_TXN#4", "sk": "ITEM#1", "value": "original"})
    dynamo.sync_put_item("test_table", {"pk": "SYNC_TXN#4", "sk": "CHECK", "status": "inactive"})

    # AND a transaction with a condition check that will fail
    operations = [
        {
            "type": "put",
            "table": "test_table",
            "item": {"pk": "SYNC_TXN#4", "sk": "ITEM#1", "value": "updated"},
        },
        {
            "type": "condition_check",
            "table": "test_table",
            "key": {"pk": "SYNC_TXN#4", "sk": "CHECK"},
            "condition_expression": "#s = :expected",
            "expression_attribute_names": {"#s": "status"},
            "expression_attribute_values": {":expected": "active"},  # Will fail
        },
    ]

    # WHEN we execute the transaction
    # THEN it fails
    with pytest.raises((TransactionCanceledException, PydynoxException)):
        dynamo.sync_transact_write(operations)

    # AND the put was rolled back - original value remains
    result = dynamo.sync_get_item("test_table", {"pk": "SYNC_TXN#4", "sk": "ITEM#1"})
    assert result is not None
    assert result["value"] == "original"


def test_sync_transact_write_condition_check_success(dynamo):
    """Test sync transaction with a passing condition check."""
    # Put initial items
    dynamo.sync_put_item("test_table", {"pk": "SYNC_TXN#5", "sk": "CHECK", "status": "active"})

    operations = [
        {
            "type": "put",
            "table": "test_table",
            "item": {"pk": "SYNC_TXN#5", "sk": "NEW", "name": "Created"},
        },
        {
            "type": "condition_check",
            "table": "test_table",
            "key": {"pk": "SYNC_TXN#5", "sk": "CHECK"},
            "condition_expression": "#s = :expected",
            "expression_attribute_names": {"#s": "status"},
            "expression_attribute_values": {":expected": "active"},
        },
    ]

    dynamo.sync_transact_write(operations)

    # Verify the put succeeded
    result = dynamo.sync_get_item("test_table", {"pk": "SYNC_TXN#5", "sk": "NEW"})
    assert result is not None
    assert result["name"] == "Created"


def test_sync_transaction_context_manager(dynamo):
    """Test SyncTransaction context manager commits on exit."""
    # WHEN we use the sync context manager
    with SyncTransaction(dynamo) as txn:
        txn.put("test_table", {"pk": "SYNC_TXN#6", "sk": "ITEM#1", "name": "Alice"})
        txn.put("test_table", {"pk": "SYNC_TXN#6", "sk": "ITEM#2", "name": "Bob"})

    # THEN items are saved
    result = dynamo.sync_get_item("test_table", {"pk": "SYNC_TXN#6", "sk": "ITEM#1"})
    assert result is not None
    assert result["name"] == "Alice"

    result = dynamo.sync_get_item("test_table", {"pk": "SYNC_TXN#6", "sk": "ITEM#2"})
    assert result is not None
    assert result["name"] == "Bob"


def test_sync_transaction_context_manager_rollback_on_exception(dynamo):
    """Test SyncTransaction context manager does not commit on exception."""
    # GIVEN an existing item
    dynamo.sync_put_item("test_table", {"pk": "SYNC_TXN#7", "sk": "ITEM", "value": "original"})

    # WHEN an exception occurs in the context
    try:
        with SyncTransaction(dynamo) as txn:
            txn.put("test_table", {"pk": "SYNC_TXN#7", "sk": "ITEM", "value": "updated"})
            raise RuntimeError("Simulated error")
    except RuntimeError:
        pass

    # THEN the put was NOT committed - original value remains
    result = dynamo.sync_get_item("test_table", {"pk": "SYNC_TXN#7", "sk": "ITEM"})
    assert result is not None
    assert result["value"] == "original"


def test_sync_transact_write_empty_operations(dynamo):
    """Test sync transaction with empty operations list does nothing."""
    # Should not raise an error
    dynamo.sync_transact_write([])


def test_sync_transact_get_multiple_items(dynamo):
    """Test sync reading multiple items atomically."""
    # GIVEN multiple items exist
    dynamo.sync_put_item("test_table", {"pk": "SYNC_TGET#1", "sk": "ITEM#1", "name": "Alice"})
    dynamo.sync_put_item("test_table", {"pk": "SYNC_TGET#1", "sk": "ITEM#2", "name": "Bob"})
    dynamo.sync_put_item("test_table", {"pk": "SYNC_TGET#1", "sk": "ITEM#3", "name": "Charlie"})

    # WHEN we read them in a sync transaction
    gets = [
        {"table": "test_table", "key": {"pk": "SYNC_TGET#1", "sk": "ITEM#1"}},
        {"table": "test_table", "key": {"pk": "SYNC_TGET#1", "sk": "ITEM#2"}},
        {"table": "test_table", "key": {"pk": "SYNC_TGET#1", "sk": "ITEM#3"}},
    ]
    results = dynamo.sync_transact_get(gets)

    # THEN all items are returned
    assert len(results) == 3
    assert results[0]["name"] == "Alice"
    assert results[1]["name"] == "Bob"
    assert results[2]["name"] == "Charlie"


def test_sync_transact_get_with_missing_item(dynamo):
    """Test sync transact_get returns None for missing items."""
    # GIVEN one item exists
    dynamo.sync_put_item("test_table", {"pk": "SYNC_TGET#2", "sk": "EXISTS", "name": "Found"})

    # WHEN we read existing and non-existing items
    gets = [
        {"table": "test_table", "key": {"pk": "SYNC_TGET#2", "sk": "EXISTS"}},
        {"table": "test_table", "key": {"pk": "SYNC_TGET#2", "sk": "MISSING"}},
    ]
    results = dynamo.sync_transact_get(gets)

    # THEN existing item is returned, missing is None
    assert len(results) == 2
    assert results[0]["name"] == "Found"
    assert results[1] is None


def test_sync_transact_get_empty_list(dynamo):
    """Test sync transact_get with empty list returns empty list."""
    results = dynamo.sync_transact_get([])
    assert results == []
