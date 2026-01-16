"""Integration tests for delete_item operation."""

import pytest
from pydynox.exceptions import ConditionalCheckFailedException, ResourceNotFoundException


def test_delete_item_removes_item(dynamo):
    """Test that delete_item removes an existing item."""
    # GIVEN an existing item
    item = {"pk": "USER#DEL1", "sk": "PROFILE", "name": "ToDelete"}
    dynamo.put_item("test_table", item)
    result = dynamo.get_item("test_table", {"pk": "USER#DEL1", "sk": "PROFILE"})
    assert result is not None

    # WHEN deleting the item
    dynamo.delete_item("test_table", {"pk": "USER#DEL1", "sk": "PROFILE"})

    # THEN the item is gone
    result = dynamo.get_item("test_table", {"pk": "USER#DEL1", "sk": "PROFILE"})
    assert result is None


def test_delete_item_nonexistent_succeeds(dynamo):
    """Test that deleting a non-existent item does not raise an error."""
    # WHEN deleting a non-existent item
    # THEN no error is raised (DynamoDB delete is idempotent)
    dynamo.delete_item("test_table", {"pk": "NONEXISTENT", "sk": "NONE"})


def test_delete_item_with_condition_success(dynamo):
    """Test delete with a condition that passes."""
    # GIVEN an item with status=inactive
    item = {"pk": "USER#DEL2", "sk": "PROFILE", "status": "inactive"}
    dynamo.put_item("test_table", item)

    # WHEN deleting with condition status=inactive
    dynamo.delete_item(
        "test_table",
        {"pk": "USER#DEL2", "sk": "PROFILE"},
        condition_expression="#s = :val",
        expression_attribute_names={"#s": "status"},
        expression_attribute_values={":val": "inactive"},
    )

    # THEN the item is deleted
    result = dynamo.get_item("test_table", {"pk": "USER#DEL2", "sk": "PROFILE"})
    assert result is None


def test_delete_item_with_condition_fails(dynamo):
    """Test delete with a condition that fails raises an error."""
    # GIVEN an item with status=active
    item = {"pk": "USER#DEL3", "sk": "PROFILE", "status": "active"}
    dynamo.put_item("test_table", item)

    # WHEN deleting with condition status=inactive
    # THEN ConditionalCheckFailedException is raised
    with pytest.raises(ConditionalCheckFailedException):
        dynamo.delete_item(
            "test_table",
            {"pk": "USER#DEL3", "sk": "PROFILE"},
            condition_expression="#s = :val",
            expression_attribute_names={"#s": "status"},
            expression_attribute_values={":val": "inactive"},
        )

    # AND item still exists
    result = dynamo.get_item("test_table", {"pk": "USER#DEL3", "sk": "PROFILE"})
    assert result is not None
    assert result["status"] == "active"


def test_delete_item_with_attribute_exists_condition(dynamo):
    """Test delete with attribute_exists condition."""
    # GIVEN an existing item
    item = {"pk": "USER#DEL4", "sk": "PROFILE", "name": "Test"}
    dynamo.put_item("test_table", item)

    # WHEN deleting with attribute_exists condition
    dynamo.delete_item(
        "test_table",
        {"pk": "USER#DEL4", "sk": "PROFILE"},
        condition_expression="attribute_exists(#pk)",
        expression_attribute_names={"#pk": "pk"},
    )

    # THEN the item is deleted
    result = dynamo.get_item("test_table", {"pk": "USER#DEL4", "sk": "PROFILE"})
    assert result is None


def test_delete_item_table_not_found(dynamo):
    """Test delete from non-existent table raises error."""
    # WHEN deleting from a non-existent table
    # THEN ResourceNotFoundException is raised
    with pytest.raises(ResourceNotFoundException):
        dynamo.delete_item("nonexistent_table", {"pk": "X", "sk": "Y"})
