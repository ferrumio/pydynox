"""Integration tests for delete_item operation."""

import pytest
from pydynox.exceptions import ConditionalCheckFailedException, ResourceNotFoundException


@pytest.mark.asyncio
async def test_delete_item_removes_item(dynamo):
    """Test that delete_item removes an existing item."""
    # GIVEN an existing item
    item = {"pk": "USER#DEL1", "sk": "PROFILE", "name": "ToDelete"}
    await dynamo.put_item("test_table", item)
    result = await dynamo.get_item("test_table", {"pk": "USER#DEL1", "sk": "PROFILE"})
    assert result is not None

    # WHEN deleting the item
    await dynamo.delete_item("test_table", {"pk": "USER#DEL1", "sk": "PROFILE"})

    # THEN the item is gone
    result = await dynamo.get_item("test_table", {"pk": "USER#DEL1", "sk": "PROFILE"})
    assert result is None


@pytest.mark.asyncio
async def test_delete_item_nonexistent_succeeds(dynamo):
    """Test that deleting a non-existent item does not raise an error."""
    # WHEN deleting a non-existent item
    # THEN no error is raised (DynamoDB delete is idempotent)
    await dynamo.delete_item("test_table", {"pk": "NONEXISTENT", "sk": "NONE"})


@pytest.mark.asyncio
async def test_delete_item_with_condition_success(dynamo):
    """Test delete with a condition that passes."""
    # GIVEN an item with status=inactive
    item = {"pk": "USER#DEL2", "sk": "PROFILE", "status": "inactive"}
    await dynamo.put_item("test_table", item)

    # WHEN deleting with condition status=inactive
    await dynamo.delete_item(
        "test_table",
        {"pk": "USER#DEL2", "sk": "PROFILE"},
        condition_expression="#s = :val",
        expression_attribute_names={"#s": "status"},
        expression_attribute_values={":val": "inactive"},
    )

    # THEN the item is deleted
    result = await dynamo.get_item("test_table", {"pk": "USER#DEL2", "sk": "PROFILE"})
    assert result is None


@pytest.mark.asyncio
async def test_delete_item_with_condition_fails(dynamo):
    """Test delete with a condition that fails raises an error."""
    # GIVEN an item with status=active
    item = {"pk": "USER#DEL3", "sk": "PROFILE", "status": "active"}
    await dynamo.put_item("test_table", item)

    # WHEN deleting with condition status=inactive
    # THEN ConditionalCheckFailedException is raised
    with pytest.raises(ConditionalCheckFailedException):
        await dynamo.delete_item(
            "test_table",
            {"pk": "USER#DEL3", "sk": "PROFILE"},
            condition_expression="#s = :val",
            expression_attribute_names={"#s": "status"},
            expression_attribute_values={":val": "inactive"},
        )

    # AND item still exists
    result = await dynamo.get_item("test_table", {"pk": "USER#DEL3", "sk": "PROFILE"})
    assert result is not None
    assert result["status"] == "active"


@pytest.mark.asyncio
async def test_delete_item_with_attribute_exists_condition(dynamo):
    """Test delete with attribute_exists condition."""
    # GIVEN an existing item
    item = {"pk": "USER#DEL4", "sk": "PROFILE", "name": "Test"}
    await dynamo.put_item("test_table", item)

    # WHEN deleting with attribute_exists condition
    await dynamo.delete_item(
        "test_table",
        {"pk": "USER#DEL4", "sk": "PROFILE"},
        condition_expression="attribute_exists(#pk)",
        expression_attribute_names={"#pk": "pk"},
    )

    # THEN the item is deleted
    result = await dynamo.get_item("test_table", {"pk": "USER#DEL4", "sk": "PROFILE"})
    assert result is None


@pytest.mark.asyncio
async def test_delete_item_table_not_found(dynamo):
    """Test delete from non-existent table raises error."""
    # WHEN deleting from a non-existent table
    # THEN ResourceNotFoundException is raised
    with pytest.raises(ResourceNotFoundException):
        await dynamo.delete_item("nonexistent_table", {"pk": "X", "sk": "Y"})
