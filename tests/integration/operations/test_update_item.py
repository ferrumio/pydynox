"""Integration tests for update_item operation."""

import pytest
from pydynox.exceptions import ConditionalCheckFailedException, ResourceNotFoundException


@pytest.mark.asyncio
async def test_update_item_simple_set(dynamo):
    """Test simple update that sets field values."""
    # GIVEN an existing item
    item = {"pk": "USER#UPD1", "sk": "PROFILE", "name": "Original", "age": 25}
    await dynamo.put_item("test_table", item)

    # WHEN updating fields
    await dynamo.update_item(
        "test_table",
        {"pk": "USER#UPD1", "sk": "PROFILE"},
        updates={"name": "Updated", "age": 30},
    )

    # THEN fields are updated
    result = await dynamo.get_item("test_table", {"pk": "USER#UPD1", "sk": "PROFILE"})
    assert result["name"] == "Updated"
    assert result["age"] == 30


@pytest.mark.asyncio
async def test_update_item_add_new_field(dynamo):
    """Test update that adds a new field."""
    # GIVEN an existing item
    item = {"pk": "USER#UPD2", "sk": "PROFILE", "name": "Test"}
    await dynamo.put_item("test_table", item)

    # WHEN adding a new field
    await dynamo.update_item(
        "test_table",
        {"pk": "USER#UPD2", "sk": "PROFILE"},
        updates={"email": "test@example.com"},
    )

    # THEN new field is added
    result = await dynamo.get_item("test_table", {"pk": "USER#UPD2", "sk": "PROFILE"})
    assert result["name"] == "Test"
    assert result["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_update_item_increment_with_expression(dynamo):
    """Test atomic increment using update expression."""
    # GIVEN an item with a counter
    item = {"pk": "USER#UPD3", "sk": "PROFILE", "counter": 10}
    await dynamo.put_item("test_table", item)

    # WHEN incrementing the counter
    await dynamo.update_item(
        "test_table",
        {"pk": "USER#UPD3", "sk": "PROFILE"},
        update_expression="SET #c = #c + :val",
        expression_attribute_names={"#c": "counter"},
        expression_attribute_values={":val": 5},
    )

    # THEN counter is incremented
    result = await dynamo.get_item("test_table", {"pk": "USER#UPD3", "sk": "PROFILE"})
    assert result["counter"] == 15


@pytest.mark.asyncio
async def test_update_item_decrement_with_expression(dynamo):
    """Test atomic decrement using update expression."""
    # GIVEN an item with a counter
    item = {"pk": "USER#UPD3B", "sk": "PROFILE", "counter": 100}
    await dynamo.put_item("test_table", item)

    # WHEN decrementing the counter
    await dynamo.update_item(
        "test_table",
        {"pk": "USER#UPD3B", "sk": "PROFILE"},
        update_expression="SET #c = #c - :val",
        expression_attribute_names={"#c": "counter"},
        expression_attribute_values={":val": 25},
    )

    # THEN counter is decremented
    result = await dynamo.get_item("test_table", {"pk": "USER#UPD3B", "sk": "PROFILE"})
    assert result["counter"] == 75


@pytest.mark.asyncio
async def test_update_item_append_to_list(dynamo):
    """Test atomic append to list using update expression."""
    # GIVEN an item with a list
    item = {"pk": "USER#UPD3C", "sk": "PROFILE", "tags": ["admin"]}
    await dynamo.put_item("test_table", item)

    # WHEN appending to the list
    await dynamo.update_item(
        "test_table",
        {"pk": "USER#UPD3C", "sk": "PROFILE"},
        update_expression="SET #t = list_append(#t, :vals)",
        expression_attribute_names={"#t": "tags"},
        expression_attribute_values={":vals": ["user", "moderator"]},
    )

    # THEN items are appended
    result = await dynamo.get_item("test_table", {"pk": "USER#UPD3C", "sk": "PROFILE"})
    assert result["tags"] == ["admin", "user", "moderator"]


@pytest.mark.asyncio
async def test_update_item_remove_attribute(dynamo):
    """Test removing an attribute using update expression."""
    # GIVEN an item with a temp field
    item = {"pk": "USER#UPD3D", "sk": "PROFILE", "name": "Test", "temp": "to_remove"}
    await dynamo.put_item("test_table", item)

    # WHEN removing the temp field
    await dynamo.update_item(
        "test_table",
        {"pk": "USER#UPD3D", "sk": "PROFILE"},
        update_expression="REMOVE #t",
        expression_attribute_names={"#t": "temp"},
    )

    # THEN temp field is removed
    result = await dynamo.get_item("test_table", {"pk": "USER#UPD3D", "sk": "PROFILE"})
    assert result["name"] == "Test"
    assert "temp" not in result


@pytest.mark.asyncio
async def test_update_item_with_condition_success(dynamo):
    """Test update with a condition that passes."""
    # GIVEN an item with status=pending
    item = {"pk": "USER#UPD4", "sk": "PROFILE", "status": "pending", "name": "Test"}
    await dynamo.put_item("test_table", item)

    # WHEN updating with condition status=pending
    await dynamo.update_item(
        "test_table",
        {"pk": "USER#UPD4", "sk": "PROFILE"},
        updates={"status": "active"},
        condition_expression="#s = :expected",
        expression_attribute_names={"#s": "status"},
        expression_attribute_values={":expected": "pending"},
    )

    # THEN update succeeds
    result = await dynamo.get_item("test_table", {"pk": "USER#UPD4", "sk": "PROFILE"})
    assert result["status"] == "active"


@pytest.mark.asyncio
async def test_update_item_with_condition_fails(dynamo):
    """Test update with a condition that fails raises an error."""
    # GIVEN an item with status=active
    item = {"pk": "USER#UPD5", "sk": "PROFILE", "status": "active"}
    await dynamo.put_item("test_table", item)

    # WHEN updating with condition status=pending
    # THEN ConditionalCheckFailedException is raised
    with pytest.raises(ConditionalCheckFailedException):
        await dynamo.update_item(
            "test_table",
            {"pk": "USER#UPD5", "sk": "PROFILE"},
            updates={"status": "inactive"},
            condition_expression="#s = :expected",
            expression_attribute_names={"#s": "status"},
            expression_attribute_values={":expected": "pending"},
        )

    # AND item is unchanged
    result = await dynamo.get_item("test_table", {"pk": "USER#UPD5", "sk": "PROFILE"})
    assert result["status"] == "active"


@pytest.mark.asyncio
async def test_update_item_multiple_types(dynamo):
    """Test update with different data types."""
    # GIVEN an existing item
    item = {"pk": "USER#UPD6", "sk": "PROFILE", "name": "Test"}
    await dynamo.put_item("test_table", item)

    # WHEN updating with various types
    await dynamo.update_item(
        "test_table",
        {"pk": "USER#UPD6", "sk": "PROFILE"},
        updates={
            "age": 30,
            "score": 95.5,
            "active": True,
            "tags": ["admin", "user"],
            "meta": {"key": "value"},
        },
    )

    # THEN all types are preserved
    result = await dynamo.get_item("test_table", {"pk": "USER#UPD6", "sk": "PROFILE"})
    assert result["age"] == 30
    assert result["score"] == 95.5
    assert result["active"] is True
    assert result["tags"] == ["admin", "user"]
    assert result["meta"] == {"key": "value"}


@pytest.mark.asyncio
async def test_update_item_nonexistent_creates_item(dynamo):
    """Test that updating a non-existent item creates it."""
    # WHEN updating a non-existent item
    await dynamo.update_item(
        "test_table",
        {"pk": "USER#NEW", "sk": "PROFILE"},
        updates={"name": "NewUser"},
    )

    # THEN item is created
    result = await dynamo.get_item("test_table", {"pk": "USER#NEW", "sk": "PROFILE"})
    assert result is not None
    assert result["name"] == "NewUser"


@pytest.mark.asyncio
async def test_update_item_table_not_found(dynamo):
    """Test update on non-existent table raises error."""
    # WHEN updating on a non-existent table
    # THEN ResourceNotFoundException is raised
    with pytest.raises(ResourceNotFoundException):
        await dynamo.update_item(
            "nonexistent_table",
            {"pk": "X", "sk": "Y"},
            updates={"name": "Test"},
        )


@pytest.mark.asyncio
async def test_update_item_no_updates_or_expression_fails(dynamo):
    """Test that update without updates or expression raises error."""
    # GIVEN an existing item
    item = {"pk": "USER#UPD7", "sk": "PROFILE", "name": "Test"}
    await dynamo.put_item("test_table", item)

    # WHEN updating without updates or expression
    # THEN ValueError is raised
    with pytest.raises(ValueError):
        await dynamo.update_item(
            "test_table",
            {"pk": "USER#UPD7", "sk": "PROFILE"},
        )
