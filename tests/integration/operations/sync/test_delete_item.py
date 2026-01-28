"""Sync integration tests for delete_item operation."""

import pytest
from pydynox.exceptions import ConditionalCheckFailedException, ResourceNotFoundException


def test_sync_delete_item_removes_item(dynamo):
    """Test that sync_delete_item removes an existing item."""
    # GIVEN an existing item
    item = {"pk": "SYNC_DEL#1", "sk": "PROFILE", "name": "ToDelete"}
    dynamo.sync_put_item("test_table", item)
    result = dynamo.sync_get_item("test_table", {"pk": "SYNC_DEL#1", "sk": "PROFILE"})
    assert result is not None

    # WHEN deleting the item
    dynamo.sync_delete_item("test_table", {"pk": "SYNC_DEL#1", "sk": "PROFILE"})

    # THEN the item is gone
    result = dynamo.sync_get_item("test_table", {"pk": "SYNC_DEL#1", "sk": "PROFILE"})
    assert result is None


def test_sync_delete_item_nonexistent_succeeds(dynamo):
    """Test that deleting a non-existent item does not raise an error."""
    # WHEN deleting a non-existent item
    # THEN no error is raised (DynamoDB delete is idempotent)
    dynamo.sync_delete_item("test_table", {"pk": "SYNC_NONEXISTENT", "sk": "NONE"})


def test_sync_delete_item_with_condition_success(dynamo):
    """Test sync delete with a condition that passes."""
    # GIVEN an item with status=inactive
    item = {"pk": "SYNC_DEL#2", "sk": "PROFILE", "status": "inactive"}
    dynamo.sync_put_item("test_table", item)

    # WHEN deleting with condition status=inactive
    dynamo.sync_delete_item(
        "test_table",
        {"pk": "SYNC_DEL#2", "sk": "PROFILE"},
        condition_expression="#s = :val",
        expression_attribute_names={"#s": "status"},
        expression_attribute_values={":val": "inactive"},
    )

    # THEN the item is deleted
    result = dynamo.sync_get_item("test_table", {"pk": "SYNC_DEL#2", "sk": "PROFILE"})
    assert result is None


def test_sync_delete_item_with_condition_fails(dynamo):
    """Test sync delete with a condition that fails raises an error."""
    # GIVEN an item with status=active
    item = {"pk": "SYNC_DEL#3", "sk": "PROFILE", "status": "active"}
    dynamo.sync_put_item("test_table", item)

    # WHEN deleting with condition status=inactive
    # THEN ConditionalCheckFailedException is raised
    with pytest.raises(ConditionalCheckFailedException):
        dynamo.sync_delete_item(
            "test_table",
            {"pk": "SYNC_DEL#3", "sk": "PROFILE"},
            condition_expression="#s = :val",
            expression_attribute_names={"#s": "status"},
            expression_attribute_values={":val": "inactive"},
        )

    # AND item still exists
    result = dynamo.sync_get_item("test_table", {"pk": "SYNC_DEL#3", "sk": "PROFILE"})
    assert result is not None
    assert result["status"] == "active"


def test_sync_delete_item_with_attribute_exists_condition(dynamo):
    """Test sync delete with attribute_exists condition."""
    # GIVEN an existing item
    item = {"pk": "SYNC_DEL#4", "sk": "PROFILE", "name": "Test"}
    dynamo.sync_put_item("test_table", item)

    # WHEN deleting with attribute_exists condition
    dynamo.sync_delete_item(
        "test_table",
        {"pk": "SYNC_DEL#4", "sk": "PROFILE"},
        condition_expression="attribute_exists(#pk)",
        expression_attribute_names={"#pk": "pk"},
    )

    # THEN the item is deleted
    result = dynamo.sync_get_item("test_table", {"pk": "SYNC_DEL#4", "sk": "PROFILE"})
    assert result is None


def test_sync_delete_item_table_not_found(dynamo):
    """Test sync delete from non-existent table raises error."""
    # WHEN deleting from a non-existent table
    # THEN ResourceNotFoundException is raised
    with pytest.raises(ResourceNotFoundException):
        dynamo.sync_delete_item("nonexistent_table", {"pk": "X", "sk": "Y"})


def test_sync_delete_item_returns_metrics(dynamo):
    """Test that sync_delete_item returns metrics."""
    # GIVEN an existing item
    item = {"pk": "SYNC_DEL_METRICS#1", "sk": "PROFILE", "name": "Test"}
    dynamo.sync_put_item("test_table", item)

    # WHEN deleting the item
    metrics = dynamo.sync_delete_item("test_table", {"pk": "SYNC_DEL_METRICS#1", "sk": "PROFILE"})

    # THEN metrics are returned
    assert metrics.duration_ms > 0
