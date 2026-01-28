"""Integration tests for batch_get operation."""

import uuid

import pytest
from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute


@pytest.mark.asyncio
async def test_batch_get_returns_items(dynamo):
    """Test batch get with a few items."""
    # GIVEN existing items
    items = [
        {"pk": "BGET#1", "sk": "ITEM#1", "name": "Alice"},
        {"pk": "BGET#1", "sk": "ITEM#2", "name": "Bob"},
        {"pk": "BGET#1", "sk": "ITEM#3", "name": "Charlie"},
    ]
    for item in items:
        await dynamo.put_item("test_table", item)

    # WHEN batch getting them
    keys = [{"pk": item["pk"], "sk": item["sk"]} for item in items]
    results = await dynamo.batch_get("test_table", keys)

    # THEN all items are returned
    assert len(results) == 3
    names = {r["name"] for r in results}
    assert names == {"Alice", "Bob", "Charlie"}


@pytest.mark.asyncio
async def test_batch_get_missing_items_not_returned(dynamo):
    """Test batch get with some missing items."""
    # GIVEN only one existing item
    await dynamo.put_item("test_table", {"pk": "MISS#1", "sk": "EXISTS", "name": "Found"})

    # WHEN batch getting two items (one exists, one doesn't)
    keys = [
        {"pk": "MISS#1", "sk": "EXISTS"},
        {"pk": "MISS#1", "sk": "NOTEXISTS"},
    ]
    results = await dynamo.batch_get("test_table", keys)

    # THEN only the existing item is returned
    assert len(results) == 1
    assert results[0]["name"] == "Found"


@pytest.mark.asyncio
async def test_batch_get_empty_keys_returns_empty(dynamo):
    """Test batch get with empty keys list."""
    # WHEN batch getting with empty keys
    results = await dynamo.batch_get("test_table", [])

    # THEN empty list is returned
    assert results == []


@pytest.mark.asyncio
async def test_batch_get_more_than_100_items(dynamo):
    """Test batch get with more than 100 items.

    DynamoDB limits batch gets to 100 items per request.
    The client should split the request into multiple batches.
    Requirements: 7.6
    """
    # GIVEN 120 items (more than the 100-item limit)
    items = [
        {"pk": "LARGE#1", "sk": f"ITEM#{i:03d}", "index": i, "data": f"value_{i}"}
        for i in range(120)
    ]
    await dynamo.batch_write("test_table", put_items=items)

    # WHEN batch getting all 120 items
    keys = [{"pk": item["pk"], "sk": item["sk"]} for item in items]
    results = await dynamo.batch_get("test_table", keys)

    # THEN all 120 items are returned
    assert len(results) == 120
    indices = {r["index"] for r in results}
    assert indices == set(range(120))


@pytest.mark.asyncio
async def test_batch_get_exactly_100_items(dynamo):
    """Test batch get with exactly 100 items (the limit)."""
    # GIVEN exactly 100 items
    items = [{"pk": "EXACT#1", "sk": f"ITEM#{i:02d}", "value": i} for i in range(100)]
    await dynamo.batch_write("test_table", put_items=items)

    # WHEN batch getting them
    keys = [{"pk": item["pk"], "sk": item["sk"]} for item in items]
    results = await dynamo.batch_get("test_table", keys)

    # THEN all 100 items are returned
    assert len(results) == 100
    values = {r["value"] for r in results}
    assert values == set(range(100))


@pytest.mark.asyncio
async def test_batch_get_150_items(dynamo):
    """Test batch get with 150 items (requires 2 batches)."""
    # GIVEN 150 items
    items = [{"pk": "ONEFIFTY#1", "sk": f"ITEM#{i:03d}", "num": i} for i in range(150)]
    await dynamo.batch_write("test_table", put_items=items)

    # WHEN batch getting them
    keys = [{"pk": item["pk"], "sk": item["sk"]} for item in items]
    results = await dynamo.batch_get("test_table", keys)

    # THEN all 150 items are returned
    assert len(results) == 150
    nums = {r["num"] for r in results}
    assert nums == set(range(150))


@pytest.mark.asyncio
async def test_batch_get_with_various_types(dynamo):
    """Test batch get with items containing various data types."""
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
    await dynamo.batch_write("test_table", put_items=items)

    # WHEN batch getting them
    keys = [{"pk": item["pk"], "sk": item["sk"]} for item in items]
    results = await dynamo.batch_get("test_table", keys)

    # THEN all types are preserved
    assert len(results) == 2
    by_sk = {r["sk"]: r for r in results}
    for item in items:
        result = by_sk[item["sk"]]
        for field, value in item.items():
            assert result[field] == value


# ========== Model.batch_get tests ==========


@pytest.fixture
def user_model(dynamo):
    """Create a User model for batch_get tests."""

    class User(Model):
        model_config = ModelConfig(table="test_table", client=dynamo)
        pk = StringAttribute(hash_key=True)
        sk = StringAttribute(range_key=True)
        name = StringAttribute()
        age = NumberAttribute()

    User._client_instance = None
    return User


@pytest.mark.asyncio
async def test_model_batch_get_returns_model_instances(dynamo, user_model):
    """Model.batch_get returns Model instances by default."""
    # GIVEN existing items
    uid = str(uuid.uuid4())
    items = [
        {"pk": f"MBGET#{uid}", "sk": "USER#1", "name": "Alice", "age": 25},
        {"pk": f"MBGET#{uid}", "sk": "USER#2", "name": "Bob", "age": 30},
        {"pk": f"MBGET#{uid}", "sk": "USER#3", "name": "Charlie", "age": 35},
    ]
    for item in items:
        await dynamo.put_item("test_table", item)

    # WHEN batch getting them
    keys = [{"pk": item["pk"], "sk": item["sk"]} for item in items]
    users = await user_model.batch_get(keys)

    # THEN Model instances are returned
    assert len(users) == 3
    for user in users:
        assert isinstance(user, user_model)
    names = {u.name for u in users}
    assert names == {"Alice", "Bob", "Charlie"}


@pytest.mark.asyncio
async def test_model_batch_get_as_dict_returns_dicts(dynamo, user_model):
    """Model.batch_get(as_dict=True) returns plain dicts."""
    # GIVEN existing items
    uid = str(uuid.uuid4())
    items = [
        {"pk": f"MBGETD#{uid}", "sk": "USER#1", "name": "Alice", "age": 25},
        {"pk": f"MBGETD#{uid}", "sk": "USER#2", "name": "Bob", "age": 30},
    ]
    for item in items:
        await dynamo.put_item("test_table", item)

    # WHEN batch getting with as_dict=True
    keys = [{"pk": item["pk"], "sk": item["sk"]} for item in items]
    users = await user_model.batch_get(keys, as_dict=True)

    # THEN plain dicts are returned
    assert len(users) == 2
    for user in users:
        assert isinstance(user, dict)
    names = {u["name"] for u in users}
    assert names == {"Alice", "Bob"}


@pytest.mark.asyncio
async def test_model_batch_get_empty_keys(user_model):
    """Model.batch_get with empty keys returns empty list."""
    # WHEN batch getting with empty keys
    users = await user_model.batch_get([])

    # THEN empty list is returned
    assert users == []


@pytest.mark.asyncio
async def test_model_batch_get_missing_items(dynamo, user_model):
    """Model.batch_get only returns existing items."""
    # GIVEN only one existing item
    uid = str(uuid.uuid4())
    await dynamo.put_item(
        "test_table",
        {"pk": f"MBGETM#{uid}", "sk": "EXISTS", "name": "Found", "age": 20},
    )

    # WHEN batch getting two items (one exists, one doesn't)
    keys = [
        {"pk": f"MBGETM#{uid}", "sk": "EXISTS"},
        {"pk": f"MBGETM#{uid}", "sk": "NOTEXISTS"},
    ]
    users = await user_model.batch_get(keys)

    # THEN only the existing item is returned
    assert len(users) == 1
    assert users[0].name == "Found"
