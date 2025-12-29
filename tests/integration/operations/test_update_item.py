"""Integration tests for update_item operation."""

import pytest

from pydynox.exceptions import ConditionCheckFailedError, TableNotFoundError


def test_update_item_simple_set(dynamo):
    """Test simple update that sets field values."""
    item = {"pk": "USER#UPD1", "sk": "PROFILE", "name": "Original", "age": 25}
    dynamo.put_item("test_table", item)

    dynamo.update_item(
        "test_table",
        {"pk": "USER#UPD1", "sk": "PROFILE"},
        updates={"name": "Updated", "age": 30},
    )

    result = dynamo.get_item("test_table", {"pk": "USER#UPD1", "sk": "PROFILE"})
    assert result["name"] == "Updated"
    assert result["age"] == 30


def test_update_item_add_new_field(dynamo):
    """Test update that adds a new field."""
    item = {"pk": "USER#UPD2", "sk": "PROFILE", "name": "Test"}
    dynamo.put_item("test_table", item)

    dynamo.update_item(
        "test_table",
        {"pk": "USER#UPD2", "sk": "PROFILE"},
        updates={"email": "test@example.com"},
    )

    result = dynamo.get_item("test_table", {"pk": "USER#UPD2", "sk": "PROFILE"})
    assert result["name"] == "Test"
    assert result["email"] == "test@example.com"


def test_update_item_increment_with_expression(dynamo):
    """Test atomic increment using update expression."""
    item = {"pk": "USER#UPD3", "sk": "PROFILE", "counter": 10}
    dynamo.put_item("test_table", item)

    dynamo.update_item(
        "test_table",
        {"pk": "USER#UPD3", "sk": "PROFILE"},
        update_expression="SET #c = #c + :val",
        expression_attribute_names={"#c": "counter"},
        expression_attribute_values={":val": 5},
    )

    result = dynamo.get_item("test_table", {"pk": "USER#UPD3", "sk": "PROFILE"})
    assert result["counter"] == 15


def test_update_item_decrement_with_expression(dynamo):
    """Test atomic decrement using update expression."""
    item = {"pk": "USER#UPD3B", "sk": "PROFILE", "counter": 100}
    dynamo.put_item("test_table", item)

    dynamo.update_item(
        "test_table",
        {"pk": "USER#UPD3B", "sk": "PROFILE"},
        update_expression="SET #c = #c - :val",
        expression_attribute_names={"#c": "counter"},
        expression_attribute_values={":val": 25},
    )

    result = dynamo.get_item("test_table", {"pk": "USER#UPD3B", "sk": "PROFILE"})
    assert result["counter"] == 75


def test_update_item_append_to_list(dynamo):
    """Test atomic append to list using update expression."""
    item = {"pk": "USER#UPD3C", "sk": "PROFILE", "tags": ["admin"]}
    dynamo.put_item("test_table", item)

    dynamo.update_item(
        "test_table",
        {"pk": "USER#UPD3C", "sk": "PROFILE"},
        update_expression="SET #t = list_append(#t, :vals)",
        expression_attribute_names={"#t": "tags"},
        expression_attribute_values={":vals": ["user", "moderator"]},
    )

    result = dynamo.get_item("test_table", {"pk": "USER#UPD3C", "sk": "PROFILE"})
    assert result["tags"] == ["admin", "user", "moderator"]


def test_update_item_remove_attribute(dynamo):
    """Test removing an attribute using update expression."""
    item = {"pk": "USER#UPD3D", "sk": "PROFILE", "name": "Test", "temp": "to_remove"}
    dynamo.put_item("test_table", item)

    dynamo.update_item(
        "test_table",
        {"pk": "USER#UPD3D", "sk": "PROFILE"},
        update_expression="REMOVE #t",
        expression_attribute_names={"#t": "temp"},
    )

    result = dynamo.get_item("test_table", {"pk": "USER#UPD3D", "sk": "PROFILE"})
    assert result["name"] == "Test"
    assert "temp" not in result


def test_update_item_with_condition_success(dynamo):
    """Test update with a condition that passes."""
    item = {"pk": "USER#UPD4", "sk": "PROFILE", "status": "pending", "name": "Test"}
    dynamo.put_item("test_table", item)

    dynamo.update_item(
        "test_table",
        {"pk": "USER#UPD4", "sk": "PROFILE"},
        updates={"status": "active"},
        condition_expression="#s = :expected",
        expression_attribute_names={"#s": "status"},
        expression_attribute_values={":expected": "pending"},
    )

    result = dynamo.get_item("test_table", {"pk": "USER#UPD4", "sk": "PROFILE"})
    assert result["status"] == "active"


def test_update_item_with_condition_fails(dynamo):
    """Test update with a condition that fails raises an error."""
    item = {"pk": "USER#UPD5", "sk": "PROFILE", "status": "active"}
    dynamo.put_item("test_table", item)

    with pytest.raises(ConditionCheckFailedError):
        dynamo.update_item(
            "test_table",
            {"pk": "USER#UPD5", "sk": "PROFILE"},
            updates={"status": "inactive"},
            condition_expression="#s = :expected",
            expression_attribute_names={"#s": "status"},
            expression_attribute_values={":expected": "pending"},
        )

    result = dynamo.get_item("test_table", {"pk": "USER#UPD5", "sk": "PROFILE"})
    assert result["status"] == "active"


def test_update_item_multiple_types(dynamo):
    """Test update with different data types."""
    item = {"pk": "USER#UPD6", "sk": "PROFILE", "name": "Test"}
    dynamo.put_item("test_table", item)

    dynamo.update_item(
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

    result = dynamo.get_item("test_table", {"pk": "USER#UPD6", "sk": "PROFILE"})
    assert result["age"] == 30
    assert result["score"] == 95.5
    assert result["active"] is True
    assert result["tags"] == ["admin", "user"]
    assert result["meta"] == {"key": "value"}


def test_update_item_nonexistent_creates_item(dynamo):
    """Test that updating a non-existent item creates it."""
    dynamo.update_item(
        "test_table",
        {"pk": "USER#NEW", "sk": "PROFILE"},
        updates={"name": "NewUser"},
    )

    result = dynamo.get_item("test_table", {"pk": "USER#NEW", "sk": "PROFILE"})
    assert result is not None
    assert result["name"] == "NewUser"


def test_update_item_table_not_found(dynamo):
    """Test update on non-existent table raises error."""
    with pytest.raises(TableNotFoundError):
        dynamo.update_item(
            "nonexistent_table",
            {"pk": "X", "sk": "Y"},
            updates={"name": "Test"},
        )


def test_update_item_no_updates_or_expression_fails(dynamo):
    """Test that update without updates or expression raises error."""
    item = {"pk": "USER#UPD7", "sk": "PROFILE", "name": "Test"}
    dynamo.put_item("test_table", item)

    with pytest.raises(ValueError):
        dynamo.update_item(
            "test_table",
            {"pk": "USER#UPD7", "sk": "PROFILE"},
        )
