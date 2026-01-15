"""Integration tests for transact_write operation.

Tests transaction success and rollback behavior.
Requirements: 9.3, 9.4
"""

import pytest
from pydynox import Transaction
from pydynox.exceptions import PydynoxError, TransactionCanceledError


def test_transact_write_puts_multiple_items(dynamo):
    """Test transaction with multiple put operations."""
    # GIVEN multiple items to put
    operations = [
        {
            "type": "put",
            "table": "test_table",
            "item": {"pk": "TXN#1", "sk": "ITEM#1", "name": "Alice"},
        },
        {
            "type": "put",
            "table": "test_table",
            "item": {"pk": "TXN#1", "sk": "ITEM#2", "name": "Bob"},
        },
        {
            "type": "put",
            "table": "test_table",
            "item": {"pk": "TXN#1", "sk": "ITEM#3", "name": "Charlie"},
        },
    ]

    # WHEN we execute the transaction
    dynamo.transact_write(operations)

    # THEN all items are saved
    for op in operations:
        item = op["item"]
        key = {"pk": item["pk"], "sk": item["sk"]}
        result = dynamo.get_item("test_table", key)
        assert result is not None
        assert result["name"] == item["name"]


def test_transact_write_with_delete(dynamo):
    """Test transaction with put and delete operations."""
    # First, put an item to delete later
    dynamo.put_item("test_table", {"pk": "TXN#2", "sk": "DELETE", "name": "ToDelete"})

    operations = [
        {
            "type": "put",
            "table": "test_table",
            "item": {"pk": "TXN#2", "sk": "NEW#1", "name": "NewItem"},
        },
        {
            "type": "delete",
            "table": "test_table",
            "key": {"pk": "TXN#2", "sk": "DELETE"},
        },
    ]

    dynamo.transact_write(operations)

    # Verify new item exists
    result = dynamo.get_item("test_table", {"pk": "TXN#2", "sk": "NEW#1"})
    assert result is not None
    assert result["name"] == "NewItem"

    # Verify deleted item is gone
    result = dynamo.get_item("test_table", {"pk": "TXN#2", "sk": "DELETE"})
    assert result is None


def test_transact_write_with_update(dynamo):
    """Test transaction with update operation."""
    # First, put an item to update
    dynamo.put_item("test_table", {"pk": "TXN#3", "sk": "UPDATE", "counter": 10})

    operations = [
        {
            "type": "update",
            "table": "test_table",
            "key": {"pk": "TXN#3", "sk": "UPDATE"},
            "update_expression": "SET #c = #c + :val",
            "expression_attribute_names": {"#c": "counter"},
            "expression_attribute_values": {":val": 5},
        },
    ]

    dynamo.transact_write(operations)

    # Verify update was applied
    result = dynamo.get_item("test_table", {"pk": "TXN#3", "sk": "UPDATE"})
    assert result is not None
    assert result["counter"] == 15


def test_transact_write_rollback_on_condition_failure(dynamo):
    """Test that transaction rolls back all operations when a condition fails.

    Requirements: 9.4
    """
    # GIVEN initial items
    dynamo.put_item("test_table", {"pk": "TXN#4", "sk": "ITEM#1", "value": "original"})
    dynamo.put_item("test_table", {"pk": "TXN#4", "sk": "CHECK", "status": "inactive"})

    # AND a transaction with a condition check that will fail
    operations = [
        {
            "type": "put",
            "table": "test_table",
            "item": {"pk": "TXN#4", "sk": "ITEM#1", "value": "updated"},
        },
        {
            "type": "condition_check",
            "table": "test_table",
            "key": {"pk": "TXN#4", "sk": "CHECK"},
            "condition_expression": "#s = :expected",
            "expression_attribute_names": {"#s": "status"},
            "expression_attribute_values": {":expected": "active"},  # Will fail
        },
    ]

    # WHEN we execute the transaction
    # THEN it fails
    with pytest.raises((TransactionCanceledError, PydynoxError)):
        dynamo.transact_write(operations)

    # AND the put was rolled back - original value remains
    result = dynamo.get_item("test_table", {"pk": "TXN#4", "sk": "ITEM#1"})
    assert result is not None
    assert result["value"] == "original"


def test_transact_write_condition_check_success(dynamo):
    """Test transaction with a passing condition check."""
    # Put initial items
    dynamo.put_item("test_table", {"pk": "TXN#5", "sk": "CHECK", "status": "active"})

    operations = [
        {
            "type": "put",
            "table": "test_table",
            "item": {"pk": "TXN#5", "sk": "NEW", "name": "Created"},
        },
        {
            "type": "condition_check",
            "table": "test_table",
            "key": {"pk": "TXN#5", "sk": "CHECK"},
            "condition_expression": "#s = :expected",
            "expression_attribute_names": {"#s": "status"},
            "expression_attribute_values": {":expected": "active"},
        },
    ]

    dynamo.transact_write(operations)

    # Verify the put succeeded
    result = dynamo.get_item("test_table", {"pk": "TXN#5", "sk": "NEW"})
    assert result is not None
    assert result["name"] == "Created"


def test_transaction_context_manager(dynamo):
    """Test Transaction context manager commits on exit."""
    # WHEN we use the context manager
    with Transaction(dynamo) as txn:
        txn.put("test_table", {"pk": "TXN#6", "sk": "ITEM#1", "name": "Alice"})
        txn.put("test_table", {"pk": "TXN#6", "sk": "ITEM#2", "name": "Bob"})

    # THEN items are saved
    result = dynamo.get_item("test_table", {"pk": "TXN#6", "sk": "ITEM#1"})
    assert result is not None
    assert result["name"] == "Alice"

    result = dynamo.get_item("test_table", {"pk": "TXN#6", "sk": "ITEM#2"})
    assert result is not None
    assert result["name"] == "Bob"


def test_transaction_context_manager_rollback_on_exception(dynamo):
    """Test Transaction context manager does not commit on exception."""
    # GIVEN an existing item
    dynamo.put_item("test_table", {"pk": "TXN#7", "sk": "ITEM", "value": "original"})

    # WHEN an exception occurs in the context
    try:
        with Transaction(dynamo) as txn:
            txn.put("test_table", {"pk": "TXN#7", "sk": "ITEM", "value": "updated"})
            raise RuntimeError("Simulated error")
    except RuntimeError:
        pass

    # THEN the put was NOT committed - original value remains
    result = dynamo.get_item("test_table", {"pk": "TXN#7", "sk": "ITEM"})
    assert result is not None
    assert result["value"] == "original"


def test_transact_write_empty_operations(dynamo):
    """Test transaction with empty operations list does nothing."""
    # Should not raise an error
    dynamo.transact_write([])
