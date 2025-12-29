"""Integration tests for delete_item operation."""

import pytest

from pydynox.exceptions import ConditionCheckFailedError, TableNotFoundError


def test_delete_item_removes_item(dynamo):
    """Test that delete_item removes an existing item."""
    item = {"pk": "USER#DEL1", "sk": "PROFILE", "name": "ToDelete"}
    dynamo.put_item("test_table", item)

    # Verify item exists
    result = dynamo.get_item("test_table", {"pk": "USER#DEL1", "sk": "PROFILE"})
    assert result is not None

    # Delete it
    dynamo.delete_item("test_table", {"pk": "USER#DEL1", "sk": "PROFILE"})

    # Verify it's gone
    result = dynamo.get_item("test_table", {"pk": "USER#DEL1", "sk": "PROFILE"})
    assert result is None


def test_delete_item_nonexistent_succeeds(dynamo):
    """Test that deleting a non-existent item does not raise an error."""
    # This should not raise - DynamoDB delete is idempotent
    dynamo.delete_item("test_table", {"pk": "NONEXISTENT", "sk": "NONE"})


def test_delete_item_with_condition_success(dynamo):
    """Test delete with a condition that passes."""
    item = {"pk": "USER#DEL2", "sk": "PROFILE", "status": "inactive"}
    dynamo.put_item("test_table", item)

    # Delete only if status is inactive
    dynamo.delete_item(
        "test_table",
        {"pk": "USER#DEL2", "sk": "PROFILE"},
        condition_expression="#s = :val",
        expression_attribute_names={"#s": "status"},
        expression_attribute_values={":val": "inactive"},
    )

    result = dynamo.get_item("test_table", {"pk": "USER#DEL2", "sk": "PROFILE"})
    assert result is None


def test_delete_item_with_condition_fails(dynamo):
    """Test delete with a condition that fails raises an error."""
    item = {"pk": "USER#DEL3", "sk": "PROFILE", "status": "active"}
    dynamo.put_item("test_table", item)

    # Try to delete only if status is inactive (it's active, so should fail)
    with pytest.raises(ConditionCheckFailedError):
        dynamo.delete_item(
            "test_table",
            {"pk": "USER#DEL3", "sk": "PROFILE"},
            condition_expression="#s = :val",
            expression_attribute_names={"#s": "status"},
            expression_attribute_values={":val": "inactive"},
        )

    # Item should still exist
    result = dynamo.get_item("test_table", {"pk": "USER#DEL3", "sk": "PROFILE"})
    assert result is not None
    assert result["status"] == "active"


def test_delete_item_with_attribute_exists_condition(dynamo):
    """Test delete with attribute_exists condition."""
    item = {"pk": "USER#DEL4", "sk": "PROFILE", "name": "Test"}
    dynamo.put_item("test_table", item)

    # Delete only if pk exists
    dynamo.delete_item(
        "test_table",
        {"pk": "USER#DEL4", "sk": "PROFILE"},
        condition_expression="attribute_exists(#pk)",
        expression_attribute_names={"#pk": "pk"},
    )

    result = dynamo.get_item("test_table", {"pk": "USER#DEL4", "sk": "PROFILE"})
    assert result is None


def test_delete_item_table_not_found(dynamo):
    """Test delete from non-existent table raises error."""
    with pytest.raises(TableNotFoundError):
        dynamo.delete_item("nonexistent_table", {"pk": "X", "sk": "Y"})
