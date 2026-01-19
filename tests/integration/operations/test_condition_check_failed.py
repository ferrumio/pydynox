"""Tests for ConditionalCheckFailedException with item return.

When a conditional write fails, DynamoDB can return the existing item
via ReturnValuesOnConditionCheckFailure. This avoids an extra GET call.
"""

import uuid

import pytest
from pydynox.exceptions import ConditionalCheckFailedException


def test_put_item_condition_failed_returns_item(dynamo):
    """put_item with condition failure returns the existing item."""
    pk = f"test-{uuid.uuid4()}"
    sk = "profile"

    # Create initial item
    dynamo.put_item("test_table", {"pk": pk, "sk": sk, "name": "Alice", "version": 1})

    # Try to put with condition that fails
    with pytest.raises(ConditionalCheckFailedException) as exc_info:
        dynamo.put_item(
            "test_table",
            {"pk": pk, "sk": sk, "name": "Bob", "version": 2},
            condition_expression="attribute_not_exists(pk)",
            return_values_on_condition_check_failure=True,
        )

    # Check that the exception has the item
    exc = exc_info.value
    assert hasattr(exc, "item"), "Exception should have 'item' attribute"
    assert exc.item is not None, "item should not be None"
    assert exc.item["pk"] == pk
    assert exc.item["sk"] == sk
    assert exc.item["name"] == "Alice"
    assert exc.item["version"] == 1


def test_put_item_condition_failed_no_item_by_default(dynamo):
    """put_item without return flag does not return item."""
    pk = f"test-{uuid.uuid4()}"
    sk = "profile"

    # Create initial item
    dynamo.put_item("test_table", {"pk": pk, "sk": sk, "name": "Alice"})

    # Try to put with condition that fails (no return flag)
    with pytest.raises(ConditionalCheckFailedException) as exc_info:
        dynamo.put_item(
            "test_table",
            {"pk": pk, "sk": sk, "name": "Bob"},
            condition_expression="attribute_not_exists(pk)",
        )

    # item attribute should be None or not set
    exc = exc_info.value
    item = getattr(exc, "item", None)
    assert item is None, "item should be None when return flag is not set"


def test_update_item_condition_failed_returns_item(dynamo):
    """update_item with condition failure returns the existing item."""
    pk = f"test-{uuid.uuid4()}"
    sk = "profile"

    # Create initial item
    dynamo.put_item("test_table", {"pk": pk, "sk": sk, "name": "Alice", "version": 1})

    # Try to update with condition that fails
    with pytest.raises(ConditionalCheckFailedException) as exc_info:
        dynamo.update_item(
            "test_table",
            {"pk": pk, "sk": sk},
            updates={"name": "Bob"},
            condition_expression="#v = :expected",
            expression_attribute_names={"#v": "version"},
            expression_attribute_values={":expected": 999},
            return_values_on_condition_check_failure=True,
        )

    exc = exc_info.value
    assert hasattr(exc, "item"), "Exception should have 'item' attribute"
    assert exc.item is not None
    assert exc.item["pk"] == pk
    assert exc.item["version"] == 1


def test_delete_item_condition_failed_returns_item(dynamo):
    """delete_item with condition failure returns the existing item."""
    pk = f"test-{uuid.uuid4()}"
    sk = "profile"

    # Create initial item
    dynamo.put_item("test_table", {"pk": pk, "sk": sk, "name": "Alice", "status": "active"})

    # Try to delete with condition that fails
    with pytest.raises(ConditionalCheckFailedException) as exc_info:
        dynamo.delete_item(
            "test_table",
            {"pk": pk, "sk": sk},
            condition_expression="#s = :expected",
            expression_attribute_names={"#s": "status"},
            expression_attribute_values={":expected": "deleted"},
            return_values_on_condition_check_failure=True,
        )

    exc = exc_info.value
    assert hasattr(exc, "item"), "Exception should have 'item' attribute"
    assert exc.item is not None
    assert exc.item["pk"] == pk
    assert exc.item["status"] == "active"


def test_optimistic_locking_pattern(dynamo):
    """Real-world pattern: optimistic locking with version check."""
    pk = f"test-{uuid.uuid4()}"
    sk = "counter"

    # Create item with version
    dynamo.put_item("test_table", {"pk": pk, "sk": sk, "count": 0, "version": 1})

    # Simulate concurrent update - first one succeeds
    dynamo.update_item(
        "test_table",
        {"pk": pk, "sk": sk},
        updates={"count": 1, "version": 2},
        condition_expression="#v = :expected",
        expression_attribute_names={"#v": "version"},
        expression_attribute_values={":expected": 1},
    )

    # Second update with stale version fails
    with pytest.raises(ConditionalCheckFailedException) as exc_info:
        dynamo.update_item(
            "test_table",
            {"pk": pk, "sk": sk},
            updates={"count": 100, "version": 2},
            condition_expression="#v = :expected",
            expression_attribute_names={"#v": "version"},
            expression_attribute_values={":expected": 1},
            return_values_on_condition_check_failure=True,
        )

    # Can see current state without extra GET
    exc = exc_info.value
    assert exc.item["version"] == 2, "Should see updated version"
    assert exc.item["count"] == 1, "Should see updated count"
