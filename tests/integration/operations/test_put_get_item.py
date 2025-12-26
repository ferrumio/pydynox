"""Integration tests for put_item and get_item operations."""

import pytest


PUT_ITEM_CASES = [
    pytest.param(
        {"pk": "USER#1", "sk": "PROFILE", "name": "John", "email": "john@test.com"},
        id="strings",
    ),
    pytest.param(
        {"pk": "USER#2", "sk": "PROFILE", "age": 30, "score": 95.5},
        id="numbers",
    ),
    pytest.param(
        {"pk": "USER#3", "sk": "SETTINGS", "active": True, "dark_mode": False},
        id="booleans",
    ),
    pytest.param(
        {"pk": "USER#4", "sk": "PROFILE", "tags": ["admin", "active"], "scores": [100, 95]},
        id="lists",
    ),
    pytest.param(
        {"pk": "USER#5", "sk": "PROFILE", "address": {"city": "Seattle", "zip": "98101"}},
        id="nested_map",
    ),
    pytest.param(
        {
            "pk": "USER#6",
            "sk": "FULL",
            "name": "Test",
            "age": 25,
            "active": True,
            "tags": ["a", "b"],
            "meta": {"key": "value"},
        },
        id="mixed_types",
    ),
]


@pytest.mark.parametrize("item", PUT_ITEM_CASES)
def test_put_item_and_get_item(dynamo, item):
    """Test saving and retrieving items with different data types."""
    dynamo.put_item("test_table", item)

    key = {"pk": item["pk"], "sk": item["sk"]}
    result = dynamo.get_item("test_table", key)

    assert result is not None
    for field, value in item.items():
        assert result[field] == value


def test_put_item_overwrites_existing(dynamo):
    """Test that put_item overwrites an existing item."""
    item1 = {"pk": "USER#100", "sk": "PROFILE", "name": "Original"}
    item2 = {"pk": "USER#100", "sk": "PROFILE", "name": "Updated", "new_field": "value"}

    dynamo.put_item("test_table", item1)
    dynamo.put_item("test_table", item2)

    result = dynamo.get_item("test_table", {"pk": "USER#100", "sk": "PROFILE"})

    assert result["name"] == "Updated"
    assert result["new_field"] == "value"


def test_get_item_not_found_returns_none(dynamo):
    """Test that get_item returns None for non-existent items."""
    result = dynamo.get_item("test_table", {"pk": "NONEXISTENT", "sk": "NONE"})
    assert result is None
