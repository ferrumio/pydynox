"""Sync integration tests for put_item operation."""

import pytest

PUT_ITEM_CASES = [
    pytest.param(
        {"pk": "SYNC_USER#1", "sk": "PROFILE", "name": "John", "email": "john@test.com"},
        id="strings",
    ),
    pytest.param(
        {"pk": "SYNC_USER#2", "sk": "PROFILE", "age": 30, "score": 95.5},
        id="numbers",
    ),
    pytest.param(
        {"pk": "SYNC_USER#3", "sk": "SETTINGS", "active": True, "dark_mode": False},
        id="booleans",
    ),
    pytest.param(
        {"pk": "SYNC_USER#4", "sk": "PROFILE", "tags": ["admin", "active"], "scores": [100, 95]},
        id="lists",
    ),
    pytest.param(
        {"pk": "SYNC_USER#5", "sk": "PROFILE", "address": {"city": "Seattle", "zip": "98101"}},
        id="nested_map",
    ),
    pytest.param(
        {
            "pk": "SYNC_USER#6",
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
def test_sync_put_item_saves_correctly(dynamo, item):
    """Test saving items with different data types using sync API."""
    # WHEN saving an item
    dynamo.sync_put_item("test_table", item)

    # THEN the item can be retrieved with all fields intact
    key = {"pk": item["pk"], "sk": item["sk"]}
    result = dynamo.sync_get_item("test_table", key)

    assert result is not None
    for field, value in item.items():
        assert result[field] == value


def test_sync_put_item_overwrites_existing(dynamo):
    """Test that sync_put_item overwrites an existing item."""
    # GIVEN an existing item
    item1 = {"pk": "SYNC_USER#100", "sk": "PROFILE", "name": "Original"}
    item2 = {"pk": "SYNC_USER#100", "sk": "PROFILE", "name": "Updated", "new_field": "value"}
    dynamo.sync_put_item("test_table", item1)

    # WHEN saving a new item with the same key
    dynamo.sync_put_item("test_table", item2)

    # THEN the item is overwritten
    result = dynamo.sync_get_item("test_table", {"pk": "SYNC_USER#100", "sk": "PROFILE"})
    assert result["name"] == "Updated"
    assert result["new_field"] == "value"


def test_sync_put_item_returns_metrics(dynamo):
    """Test that sync_put_item returns metrics."""
    item = {"pk": "SYNC_METRICS#1", "sk": "PROFILE", "name": "Test"}

    # WHEN saving an item
    metrics = dynamo.sync_put_item("test_table", item)

    # THEN metrics are returned
    assert metrics.duration_ms > 0
