"""Integration tests for get_item operation."""

import pytest

GET_ITEM_CASES = [
    pytest.param(
        {"pk": "GET#1", "sk": "PROFILE", "name": "Alice"},
        id="simple",
    ),
    pytest.param(
        {"pk": "GET#2", "sk": "DATA", "count": 42, "ratio": 3.14},
        id="numbers",
    ),
    pytest.param(
        {"pk": "GET#3", "sk": "FLAGS", "enabled": True},
        id="boolean",
    ),
    pytest.param(
        {"pk": "GET#4", "sk": "LIST", "items": ["a", "b", "c"]},
        id="list",
    ),
    pytest.param(
        {"pk": "GET#5", "sk": "MAP", "nested": {"key": "value", "num": 1}},
        id="nested_map",
    ),
]


@pytest.mark.parametrize("item", GET_ITEM_CASES)
def test_get_item_retrieves_correctly(dynamo, item):
    """Test retrieving items with different data types."""
    # Setup: save the item first
    dynamo.put_item("test_table", item)

    # Test: get the item
    key = {"pk": item["pk"], "sk": item["sk"]}
    result = dynamo.get_item("test_table", key)

    assert result is not None
    for field, value in item.items():
        assert result[field] == value


def test_get_item_not_found_returns_none(dynamo):
    """Test that get_item returns None for non-existent items."""
    result = dynamo.get_item("test_table", {"pk": "NONEXISTENT", "sk": "NONE"})
    assert result is None


def test_get_item_with_partial_key(dynamo):
    """Test get_item only returns exact key match."""
    dynamo.put_item("test_table", {"pk": "PARTIAL#1", "sk": "A", "data": "first"})
    dynamo.put_item("test_table", {"pk": "PARTIAL#1", "sk": "B", "data": "second"})

    result = dynamo.get_item("test_table", {"pk": "PARTIAL#1", "sk": "A"})

    assert result is not None
    assert result["data"] == "first"
