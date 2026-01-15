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
    # GIVEN an item saved in DynamoDB
    dynamo.put_item("test_table", item)

    # WHEN getting the item by key
    key = {"pk": item["pk"], "sk": item["sk"]}
    result = dynamo.get_item("test_table", key)

    # THEN all fields match
    assert result is not None
    for field, value in item.items():
        assert result[field] == value


def test_get_item_not_found_returns_none(dynamo):
    """Test that get_item returns None for non-existent items."""
    # WHEN getting a non-existent item
    result = dynamo.get_item("test_table", {"pk": "NONEXISTENT", "sk": "NONE"})

    # THEN None is returned
    assert result is None


def test_get_item_with_partial_key(dynamo):
    """Test get_item only returns exact key match."""
    # GIVEN two items with same pk but different sk
    dynamo.put_item("test_table", {"pk": "PARTIAL#1", "sk": "A", "data": "first"})
    dynamo.put_item("test_table", {"pk": "PARTIAL#1", "sk": "B", "data": "second"})

    # WHEN getting with specific sk
    result = dynamo.get_item("test_table", {"pk": "PARTIAL#1", "sk": "A"})

    # THEN only the exact match is returned
    assert result is not None
    assert result["data"] == "first"


def test_get_item_eventually_consistent(dynamo):
    """Test get_item with eventually consistent read (default)."""
    # GIVEN an item in DynamoDB
    dynamo.put_item("test_table", {"pk": "CONSISTENT#1", "sk": "TEST", "data": "value"})

    # WHEN getting with default consistency
    result = dynamo.get_item(
        "test_table",
        {"pk": "CONSISTENT#1", "sk": "TEST"},
    )

    # THEN item is returned
    assert result is not None
    assert result["data"] == "value"


def test_get_item_strongly_consistent(dynamo):
    """Test get_item with strongly consistent read."""
    # GIVEN an item in DynamoDB
    dynamo.put_item("test_table", {"pk": "CONSISTENT#2", "sk": "TEST", "data": "value"})

    # WHEN getting with consistent_read=True
    result = dynamo.get_item(
        "test_table",
        {"pk": "CONSISTENT#2", "sk": "TEST"},
        consistent_read=True,
    )

    # THEN item is returned
    assert result is not None
    assert result["data"] == "value"


def test_get_item_consistent_read_not_found(dynamo):
    """Test get_item with consistent_read returns None for non-existent items."""
    # WHEN getting a non-existent item with consistent_read
    result = dynamo.get_item(
        "test_table",
        {"pk": "NONEXISTENT", "sk": "NONE"},
        consistent_read=True,
    )

    # THEN None is returned
    assert result is None
