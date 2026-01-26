"""Integration tests for sync_batch_write operation."""


def test_sync_batch_write_puts_items(dynamo):
    """Test sync batch write with a few items."""
    # GIVEN a list of items
    items = [
        {"pk": "BATCH#1", "sk": "ITEM#1", "name": "Alice"},
        {"pk": "BATCH#1", "sk": "ITEM#2", "name": "Bob"},
        {"pk": "BATCH#1", "sk": "ITEM#3", "name": "Charlie"},
    ]

    # WHEN sync batch writing them
    dynamo.sync_batch_write("test_table", put_items=items)

    # THEN all items are saved
    for item in items:
        key = {"pk": item["pk"], "sk": item["sk"]}
        result = dynamo.get_item("test_table", key)
        assert result is not None
        assert result["name"] == item["name"]


def test_sync_batch_write_deletes_items(dynamo):
    """Test sync batch write with delete operations."""
    # GIVEN existing items
    items = [
        {"pk": "DEL#1", "sk": "ITEM#1", "name": "ToDelete1"},
        {"pk": "DEL#1", "sk": "ITEM#2", "name": "ToDelete2"},
        {"pk": "DEL#1", "sk": "ITEM#3", "name": "ToDelete3"},
    ]
    for item in items:
        dynamo.put_item("test_table", item)

    # WHEN sync batch deleting them
    delete_keys = [{"pk": item["pk"], "sk": item["sk"]} for item in items]
    dynamo.sync_batch_write("test_table", delete_keys=delete_keys)

    # THEN all items are deleted
    for key in delete_keys:
        result = dynamo.get_item("test_table", key)
        assert result is None


def test_sync_batch_write_mixed_operations(dynamo):
    """Test sync batch write with both puts and deletes."""
    # GIVEN an existing item to delete
    to_delete = {"pk": "MIX#1", "sk": "DELETE", "name": "WillBeDeleted"}
    dynamo.put_item("test_table", to_delete)

    # WHEN sync batch writing puts and deletes
    new_items = [
        {"pk": "MIX#1", "sk": "NEW#1", "name": "NewItem1"},
        {"pk": "MIX#1", "sk": "NEW#2", "name": "NewItem2"},
    ]
    delete_keys = [{"pk": "MIX#1", "sk": "DELETE"}]
    dynamo.sync_batch_write("test_table", put_items=new_items, delete_keys=delete_keys)

    # THEN new items exist and deleted item is gone
    for item in new_items:
        key = {"pk": item["pk"], "sk": item["sk"]}
        result = dynamo.get_item("test_table", key)
        assert result is not None
        assert result["name"] == item["name"]

    result = dynamo.get_item("test_table", {"pk": "MIX#1", "sk": "DELETE"})
    assert result is None


def test_sync_batch_write_more_than_25_items(dynamo):
    """Test sync batch write with more than 25 items.

    DynamoDB limits batch writes to 25 items per request.
    The client should split the request into multiple batches.
    Requirements: 7.3
    """
    # GIVEN 30 items (more than the 25-item limit)
    items = [
        {"pk": "LARGE#1", "sk": f"ITEM#{i:03d}", "index": i, "data": f"value_{i}"}
        for i in range(30)
    ]

    # WHEN sync batch writing them
    dynamo.sync_batch_write("test_table", put_items=items)

    # THEN all 30 items are saved
    for item in items:
        key = {"pk": item["pk"], "sk": item["sk"]}
        result = dynamo.get_item("test_table", key)
        assert result is not None
        assert result["index"] == item["index"]
        assert result["data"] == item["data"]


def test_sync_batch_write_exactly_25_items(dynamo):
    """Test sync batch write with exactly 25 items (the limit)."""
    # GIVEN exactly 25 items
    items = [{"pk": "EXACT#1", "sk": f"ITEM#{i:02d}", "value": i} for i in range(25)]

    # WHEN sync batch writing them
    dynamo.sync_batch_write("test_table", put_items=items)

    # THEN all items are saved
    for item in items:
        key = {"pk": item["pk"], "sk": item["sk"]}
        result = dynamo.get_item("test_table", key)
        assert result is not None
        assert result["value"] == item["value"]


def test_sync_batch_write_50_items(dynamo):
    """Test sync batch write with 50 items (requires 2 batches)."""
    # GIVEN 50 items
    items = [{"pk": "FIFTY#1", "sk": f"ITEM#{i:03d}", "num": i} for i in range(50)]

    # WHEN sync batch writing them
    dynamo.sync_batch_write("test_table", put_items=items)

    # THEN all 50 items are saved
    for item in items:
        key = {"pk": item["pk"], "sk": item["sk"]}
        result = dynamo.get_item("test_table", key)
        assert result is not None
        assert result["num"] == item["num"]


def test_sync_batch_write_empty_lists(dynamo):
    """Test sync batch write with empty lists does nothing."""
    # WHEN sync batch writing empty lists
    # THEN no error is raised
    dynamo.sync_batch_write("test_table", put_items=[], delete_keys=[])


def test_sync_batch_write_with_various_types(dynamo):
    """Test sync batch write with items containing various data types."""
    # GIVEN items with various data types
    items = [
        {
            "pk": "TYPES#1",
            "sk": "ITEM#1",
            "string": "hello",
            "number": 42,
            "float": 3.14,
            "bool": True,
            "list": [1, 2, 3],
            "map": {"nested": "value"},
        },
        {
            "pk": "TYPES#1",
            "sk": "ITEM#2",
            "string": "world",
            "number": -100,
            "float": 0.001,
            "bool": False,
            "list": ["a", "b"],
            "map": {"key": 123},
        },
    ]

    # WHEN sync batch writing them
    dynamo.sync_batch_write("test_table", put_items=items)

    # THEN all types are preserved
    for item in items:
        key = {"pk": item["pk"], "sk": item["sk"]}
        result = dynamo.get_item("test_table", key)
        assert result is not None
        for field, value in item.items():
            assert result[field] == value
