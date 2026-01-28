"""Sync integration tests for update_item operation."""

import pytest
from pydynox.exceptions import ConditionalCheckFailedException, ResourceNotFoundException


def test_sync_update_item_simple_set(dynamo):
    """Test simple sync update that sets field values."""
    # GIVEN an existing item
    item = {"pk": "SYNC_UPD#1", "sk": "PROFILE", "name": "Original", "age": 25}
    dynamo.sync_put_item("test_table", item)

    # WHEN updating fields
    dynamo.sync_update_item(
        "test_table",
        {"pk": "SYNC_UPD#1", "sk": "PROFILE"},
        updates={"name": "Updated", "age": 30},
    )

    # THEN fields are updated
    result = dynamo.sync_get_item("test_table", {"pk": "SYNC_UPD#1", "sk": "PROFILE"})
    assert result["name"] == "Updated"
    assert result["age"] == 30


def test_sync_update_item_add_new_field(dynamo):
    """Test sync update that adds a new field."""
    # GIVEN an existing item
    item = {"pk": "SYNC_UPD#2", "sk": "PROFILE", "name": "Test"}
    dynamo.sync_put_item("test_table", item)

    # WHEN adding a new field
    dynamo.sync_update_item(
        "test_table",
        {"pk": "SYNC_UPD#2", "sk": "PROFILE"},
        updates={"email": "test@example.com"},
    )

    # THEN new field is added
    result = dynamo.sync_get_item("test_table", {"pk": "SYNC_UPD#2", "sk": "PROFILE"})
    assert result["name"] == "Test"
    assert result["email"] == "test@example.com"


def test_sync_update_item_increment_with_expression(dynamo):
    """Test atomic increment using sync update expression."""
    # GIVEN an item with a counter
    item = {"pk": "SYNC_UPD#3", "sk": "PROFILE", "counter": 10}
    dynamo.sync_put_item("test_table", item)

    # WHEN incrementing the counter
    dynamo.sync_update_item(
        "test_table",
        {"pk": "SYNC_UPD#3", "sk": "PROFILE"},
        update_expression="SET #c = #c + :val",
        expression_attribute_names={"#c": "counter"},
        expression_attribute_values={":val": 5},
    )

    # THEN counter is incremented
    result = dynamo.sync_get_item("test_table", {"pk": "SYNC_UPD#3", "sk": "PROFILE"})
    assert result["counter"] == 15


def test_sync_update_item_decrement_with_expression(dynamo):
    """Test atomic decrement using sync update expression."""
    # GIVEN an item with a counter
    item = {"pk": "SYNC_UPD#3B", "sk": "PROFILE", "counter": 100}
    dynamo.sync_put_item("test_table", item)

    # WHEN decrementing the counter
    dynamo.sync_update_item(
        "test_table",
        {"pk": "SYNC_UPD#3B", "sk": "PROFILE"},
        update_expression="SET #c = #c - :val",
        expression_attribute_names={"#c": "counter"},
        expression_attribute_values={":val": 25},
    )

    # THEN counter is decremented
    result = dynamo.sync_get_item("test_table", {"pk": "SYNC_UPD#3B", "sk": "PROFILE"})
    assert result["counter"] == 75


def test_sync_update_item_append_to_list(dynamo):
    """Test atomic append to list using sync update expression."""
    # GIVEN an item with a list
    item = {"pk": "SYNC_UPD#3C", "sk": "PROFILE", "tags": ["admin"]}
    dynamo.sync_put_item("test_table", item)

    # WHEN appending to the list
    dynamo.sync_update_item(
        "test_table",
        {"pk": "SYNC_UPD#3C", "sk": "PROFILE"},
        update_expression="SET #t = list_append(#t, :vals)",
        expression_attribute_names={"#t": "tags"},
        expression_attribute_values={":vals": ["user", "moderator"]},
    )

    # THEN items are appended
    result = dynamo.sync_get_item("test_table", {"pk": "SYNC_UPD#3C", "sk": "PROFILE"})
    assert result["tags"] == ["admin", "user", "moderator"]


def test_sync_update_item_remove_attribute(dynamo):
    """Test removing an attribute using sync update expression."""
    # GIVEN an item with a temp field
    item = {"pk": "SYNC_UPD#3D", "sk": "PROFILE", "name": "Test", "temp": "to_remove"}
    dynamo.sync_put_item("test_table", item)

    # WHEN removing the temp field
    dynamo.sync_update_item(
        "test_table",
        {"pk": "SYNC_UPD#3D", "sk": "PROFILE"},
        update_expression="REMOVE #t",
        expression_attribute_names={"#t": "temp"},
    )

    # THEN temp field is removed
    result = dynamo.sync_get_item("test_table", {"pk": "SYNC_UPD#3D", "sk": "PROFILE"})
    assert result["name"] == "Test"
    assert "temp" not in result


def test_sync_update_item_with_condition_success(dynamo):
    """Test sync update with a condition that passes."""
    # GIVEN an item with status=pending
    item = {"pk": "SYNC_UPD#4", "sk": "PROFILE", "status": "pending", "name": "Test"}
    dynamo.sync_put_item("test_table", item)

    # WHEN updating with condition status=pending
    dynamo.sync_update_item(
        "test_table",
        {"pk": "SYNC_UPD#4", "sk": "PROFILE"},
        updates={"status": "active"},
        condition_expression="#s = :expected",
        expression_attribute_names={"#s": "status"},
        expression_attribute_values={":expected": "pending"},
    )

    # THEN update succeeds
    result = dynamo.sync_get_item("test_table", {"pk": "SYNC_UPD#4", "sk": "PROFILE"})
    assert result["status"] == "active"


def test_sync_update_item_with_condition_fails(dynamo):
    """Test sync update with a condition that fails raises an error."""
    # GIVEN an item with status=active
    item = {"pk": "SYNC_UPD#5", "sk": "PROFILE", "status": "active"}
    dynamo.sync_put_item("test_table", item)

    # WHEN updating with condition status=pending
    # THEN ConditionalCheckFailedException is raised
    with pytest.raises(ConditionalCheckFailedException):
        dynamo.sync_update_item(
            "test_table",
            {"pk": "SYNC_UPD#5", "sk": "PROFILE"},
            updates={"status": "inactive"},
            condition_expression="#s = :expected",
            expression_attribute_names={"#s": "status"},
            expression_attribute_values={":expected": "pending"},
        )

    # AND item is unchanged
    result = dynamo.sync_get_item("test_table", {"pk": "SYNC_UPD#5", "sk": "PROFILE"})
    assert result["status"] == "active"


def test_sync_update_item_multiple_types(dynamo):
    """Test sync update with different data types."""
    # GIVEN an existing item
    item = {"pk": "SYNC_UPD#6", "sk": "PROFILE", "name": "Test"}
    dynamo.sync_put_item("test_table", item)

    # WHEN updating with various types
    dynamo.sync_update_item(
        "test_table",
        {"pk": "SYNC_UPD#6", "sk": "PROFILE"},
        updates={
            "age": 30,
            "score": 95.5,
            "active": True,
            "tags": ["admin", "user"],
            "meta": {"key": "value"},
        },
    )

    # THEN all types are preserved
    result = dynamo.sync_get_item("test_table", {"pk": "SYNC_UPD#6", "sk": "PROFILE"})
    assert result["age"] == 30
    assert result["score"] == 95.5
    assert result["active"] is True
    assert result["tags"] == ["admin", "user"]
    assert result["meta"] == {"key": "value"}


def test_sync_update_item_nonexistent_creates_item(dynamo):
    """Test that sync updating a non-existent item creates it."""
    # WHEN updating a non-existent item
    dynamo.sync_update_item(
        "test_table",
        {"pk": "SYNC_NEW#1", "sk": "PROFILE"},
        updates={"name": "NewUser"},
    )

    # THEN item is created
    result = dynamo.sync_get_item("test_table", {"pk": "SYNC_NEW#1", "sk": "PROFILE"})
    assert result is not None
    assert result["name"] == "NewUser"


def test_sync_update_item_table_not_found(dynamo):
    """Test sync update on non-existent table raises error."""
    # WHEN updating on a non-existent table
    # THEN ResourceNotFoundException is raised
    with pytest.raises(ResourceNotFoundException):
        dynamo.sync_update_item(
            "nonexistent_table",
            {"pk": "X", "sk": "Y"},
            updates={"name": "Test"},
        )


def test_sync_update_item_no_updates_or_expression_fails(dynamo):
    """Test that sync update without updates or expression raises error."""
    # GIVEN an existing item
    item = {"pk": "SYNC_UPD#7", "sk": "PROFILE", "name": "Test"}
    dynamo.sync_put_item("test_table", item)

    # WHEN updating without updates or expression
    # THEN ValueError is raised
    with pytest.raises(ValueError):
        dynamo.sync_update_item(
            "test_table",
            {"pk": "SYNC_UPD#7", "sk": "PROFILE"},
        )


def test_sync_update_item_returns_metrics(dynamo):
    """Test that sync_update_item returns metrics."""
    # GIVEN an existing item
    item = {"pk": "SYNC_UPD_METRICS#1", "sk": "PROFILE", "name": "Test"}
    dynamo.sync_put_item("test_table", item)

    # WHEN updating the item
    metrics = dynamo.sync_update_item(
        "test_table",
        {"pk": "SYNC_UPD_METRICS#1", "sk": "PROFILE"},
        updates={"name": "Updated"},
    )

    # THEN metrics are returned
    assert metrics.duration_ms > 0
