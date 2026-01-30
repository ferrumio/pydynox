"""Tests for async batch operations (default, no prefix)."""

import uuid

import pytest
from pydynox import BatchWriter, DynamoDBClient, Model, ModelConfig, set_default_client
from pydynox.attributes import NumberAttribute, StringAttribute

TABLE_NAME = "async_test_users"


@pytest.fixture
def async_table(dynamo: DynamoDBClient):
    """Create a test table for async tests."""
    set_default_client(dynamo)
    if not dynamo.sync_table_exists(TABLE_NAME):
        dynamo.sync_create_table(
            TABLE_NAME,
            partition_key=("pk", "S"),
            sort_key=("sk", "S"),
            wait=True,
        )
    yield dynamo


class AsyncUser(Model):
    model_config = ModelConfig(table=TABLE_NAME)
    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
    name = StringAttribute()
    age = NumberAttribute()


# ========== Client batch_get tests (async default) ==========


@pytest.mark.asyncio
async def test_batch_get_returns_items(async_table: DynamoDBClient):
    """Test async batch get with a few items."""
    uid = str(uuid.uuid4())[:8]
    items = [
        {"pk": f"ABGET#{uid}", "sk": "ITEM#1", "name": "Alice"},
        {"pk": f"ABGET#{uid}", "sk": "ITEM#2", "name": "Bob"},
        {"pk": f"ABGET#{uid}", "sk": "ITEM#3", "name": "Charlie"},
    ]
    for item in items:
        await async_table.put_item(TABLE_NAME, item)

    keys = [{"pk": item["pk"], "sk": item["sk"]} for item in items]
    results = await async_table.batch_get(TABLE_NAME, keys)

    assert len(results) == 3
    names = {r["name"] for r in results}
    assert names == {"Alice", "Bob", "Charlie"}


@pytest.mark.asyncio
async def test_batch_get_missing_items(async_table: DynamoDBClient):
    """Test async batch get with some missing items."""
    uid = str(uuid.uuid4())[:8]
    await async_table.put_item(TABLE_NAME, {"pk": f"AMISS#{uid}", "sk": "EXISTS", "name": "Found"})

    keys = [
        {"pk": f"AMISS#{uid}", "sk": "EXISTS"},
        {"pk": f"AMISS#{uid}", "sk": "NOTEXISTS"},
    ]
    results = await async_table.batch_get(TABLE_NAME, keys)

    assert len(results) == 1
    assert results[0]["name"] == "Found"


@pytest.mark.asyncio
async def test_batch_get_empty_keys(async_table: DynamoDBClient):
    """Test async batch get with empty keys list."""
    results = await async_table.batch_get(TABLE_NAME, [])
    assert results == []


@pytest.mark.asyncio
async def test_batch_get_more_than_100_items(async_table: DynamoDBClient):
    """Test async batch get with more than 100 items."""
    uid = str(uuid.uuid4())[:8]
    items = [{"pk": f"ALARGE#{uid}", "sk": f"ITEM#{i:03d}", "index": i} for i in range(120)]
    # Use sync batch_write for setup (faster)
    async_table.sync_batch_write(TABLE_NAME, put_items=items)

    keys = [{"pk": item["pk"], "sk": item["sk"]} for item in items]
    results = await async_table.batch_get(TABLE_NAME, keys)

    assert len(results) == 120
    indices = {r["index"] for r in results}
    assert indices == set(range(120))


# ========== Client batch_write tests (async default) ==========


@pytest.mark.asyncio
async def test_batch_write_puts_items(async_table: DynamoDBClient):
    """Test async batch write with a few items."""
    uid = str(uuid.uuid4())[:8]
    items = [
        {"pk": f"ABATCH#{uid}", "sk": "ITEM#1", "name": "Alice"},
        {"pk": f"ABATCH#{uid}", "sk": "ITEM#2", "name": "Bob"},
        {"pk": f"ABATCH#{uid}", "sk": "ITEM#3", "name": "Charlie"},
    ]

    await async_table.batch_write(TABLE_NAME, put_items=items)

    for item in items:
        key = {"pk": item["pk"], "sk": item["sk"]}
        result = await async_table.get_item(TABLE_NAME, key)
        assert result is not None
        assert result["name"] == item["name"]


@pytest.mark.asyncio
async def test_batch_write_deletes_items(async_table: DynamoDBClient):
    """Test async batch write with delete operations."""
    uid = str(uuid.uuid4())[:8]
    items = [
        {"pk": f"ADEL#{uid}", "sk": "ITEM#1", "name": "ToDelete1"},
        {"pk": f"ADEL#{uid}", "sk": "ITEM#2", "name": "ToDelete2"},
    ]
    for item in items:
        await async_table.put_item(TABLE_NAME, item)

    delete_keys = [{"pk": item["pk"], "sk": item["sk"]} for item in items]
    await async_table.batch_write(TABLE_NAME, delete_keys=delete_keys)

    for key in delete_keys:
        result = await async_table.get_item(TABLE_NAME, key)
        assert result is None


@pytest.mark.asyncio
async def test_batch_write_mixed_operations(async_table: DynamoDBClient):
    """Test async batch write with both puts and deletes."""
    uid = str(uuid.uuid4())[:8]
    to_delete = {"pk": f"AMIX#{uid}", "sk": "DELETE", "name": "WillBeDeleted"}
    await async_table.put_item(TABLE_NAME, to_delete)

    new_items = [
        {"pk": f"AMIX#{uid}", "sk": "NEW#1", "name": "NewItem1"},
        {"pk": f"AMIX#{uid}", "sk": "NEW#2", "name": "NewItem2"},
    ]
    delete_keys = [{"pk": f"AMIX#{uid}", "sk": "DELETE"}]
    await async_table.batch_write(TABLE_NAME, put_items=new_items, delete_keys=delete_keys)

    for item in new_items:
        key = {"pk": item["pk"], "sk": item["sk"]}
        result = await async_table.get_item(TABLE_NAME, key)
        assert result is not None

    result = await async_table.get_item(TABLE_NAME, {"pk": f"AMIX#{uid}", "sk": "DELETE"})
    assert result is None


@pytest.mark.asyncio
async def test_batch_write_more_than_25_items(async_table: DynamoDBClient):
    """Test async batch write with more than 25 items."""
    uid = str(uuid.uuid4())[:8]
    items = [{"pk": f"A25#{uid}", "sk": f"ITEM#{i:03d}", "index": i} for i in range(30)]

    await async_table.batch_write(TABLE_NAME, put_items=items)

    for item in items:
        key = {"pk": item["pk"], "sk": item["sk"]}
        result = await async_table.get_item(TABLE_NAME, key)
        assert result is not None
        assert result["index"] == item["index"]


# ========== BatchWriter tests (async default) ==========


@pytest.mark.asyncio
async def test_batch_writer_puts_items(async_table: DynamoDBClient):
    """Test BatchWriter with put operations."""
    uid = str(uuid.uuid4())[:8]

    async with BatchWriter(async_table, TABLE_NAME) as batch:
        for i in range(5):
            batch.put({"pk": f"ABW#{uid}", "sk": f"ITEM#{i}", "name": f"User {i}"})

    for i in range(5):
        result = await async_table.get_item(TABLE_NAME, {"pk": f"ABW#{uid}", "sk": f"ITEM#{i}"})
        assert result is not None
        assert result["name"] == f"User {i}"


@pytest.mark.asyncio
async def test_batch_writer_deletes_items(async_table: DynamoDBClient):
    """Test BatchWriter with delete operations."""
    uid = str(uuid.uuid4())[:8]
    for i in range(3):
        await async_table.put_item(
            TABLE_NAME, {"pk": f"ABWD#{uid}", "sk": f"ITEM#{i}", "name": f"User {i}"}
        )

    async with BatchWriter(async_table, TABLE_NAME) as batch:
        for i in range(3):
            batch.delete({"pk": f"ABWD#{uid}", "sk": f"ITEM#{i}"})

    for i in range(3):
        result = await async_table.get_item(TABLE_NAME, {"pk": f"ABWD#{uid}", "sk": f"ITEM#{i}"})
        assert result is None


@pytest.mark.asyncio
async def test_batch_writer_mixed_operations(async_table: DynamoDBClient):
    """Test BatchWriter with mixed put and delete."""
    uid = str(uuid.uuid4())[:8]
    await async_table.put_item(TABLE_NAME, {"pk": f"ABWM#{uid}", "sk": "OLD", "name": "ToDelete"})

    async with BatchWriter(async_table, TABLE_NAME) as batch:
        batch.put({"pk": f"ABWM#{uid}", "sk": "NEW#1", "name": "New1"})
        batch.put({"pk": f"ABWM#{uid}", "sk": "NEW#2", "name": "New2"})
        batch.delete({"pk": f"ABWM#{uid}", "sk": "OLD"})

    assert await async_table.get_item(TABLE_NAME, {"pk": f"ABWM#{uid}", "sk": "NEW#1"})
    assert await async_table.get_item(TABLE_NAME, {"pk": f"ABWM#{uid}", "sk": "NEW#2"})
    assert await async_table.get_item(TABLE_NAME, {"pk": f"ABWM#{uid}", "sk": "OLD"}) is None


@pytest.mark.asyncio
async def test_batch_writer_manual_flush(async_table: DynamoDBClient):
    """Test BatchWriter manual flush."""
    uid = str(uuid.uuid4())[:8]

    async with BatchWriter(async_table, TABLE_NAME) as batch:
        batch.put({"pk": f"ABWF#{uid}", "sk": "ITEM#1", "name": "First"})
        await batch.flush()

        # Item should exist after flush
        result = await async_table.get_item(TABLE_NAME, {"pk": f"ABWF#{uid}", "sk": "ITEM#1"})
        assert result is not None

        batch.put({"pk": f"ABWF#{uid}", "sk": "ITEM#2", "name": "Second"})

    # Both items should exist
    result = await async_table.get_item(TABLE_NAME, {"pk": f"ABWF#{uid}", "sk": "ITEM#2"})
    assert result is not None


# ========== Model.batch_get tests (async default) ==========


@pytest.mark.asyncio
async def test_model_batch_get_returns_instances(async_table: DynamoDBClient):
    """Model.batch_get returns Model instances by default."""
    uid = str(uuid.uuid4())[:8]
    items = [
        {"pk": f"MABG#{uid}", "sk": "USER#1", "name": "Alice", "age": 25},
        {"pk": f"MABG#{uid}", "sk": "USER#2", "name": "Bob", "age": 30},
        {"pk": f"MABG#{uid}", "sk": "USER#3", "name": "Charlie", "age": 35},
    ]
    for item in items:
        await async_table.put_item(TABLE_NAME, item)

    keys = [{"pk": item["pk"], "sk": item["sk"]} for item in items]
    users = await AsyncUser.batch_get(keys)

    assert len(users) == 3
    for user in users:
        assert isinstance(user, AsyncUser)
    names = {u.name for u in users}
    assert names == {"Alice", "Bob", "Charlie"}


@pytest.mark.asyncio
async def test_model_batch_get_as_dict(async_table: DynamoDBClient):
    """Model.batch_get(as_dict=True) returns plain dicts."""
    uid = str(uuid.uuid4())[:8]
    items = [
        {"pk": f"MABGD#{uid}", "sk": "USER#1", "name": "Alice", "age": 25},
        {"pk": f"MABGD#{uid}", "sk": "USER#2", "name": "Bob", "age": 30},
    ]
    for item in items:
        await async_table.put_item(TABLE_NAME, item)

    keys = [{"pk": item["pk"], "sk": item["sk"]} for item in items]
    users = await AsyncUser.batch_get(keys, as_dict=True)

    assert len(users) == 2
    for user in users:
        assert isinstance(user, dict)
    names = {u["name"] for u in users}
    assert names == {"Alice", "Bob"}


@pytest.mark.asyncio
async def test_model_batch_get_empty_keys(async_table: DynamoDBClient):
    """Model.batch_get with empty keys returns empty list."""
    users = await AsyncUser.batch_get([])
    assert users == []


@pytest.mark.asyncio
async def test_model_batch_get_missing_items(async_table: DynamoDBClient):
    """Model.batch_get only returns existing items."""
    uid = str(uuid.uuid4())[:8]
    await async_table.put_item(
        TABLE_NAME,
        {"pk": f"MABGM#{uid}", "sk": "EXISTS", "name": "Found", "age": 20},
    )

    keys = [
        {"pk": f"MABGM#{uid}", "sk": "EXISTS"},
        {"pk": f"MABGM#{uid}", "sk": "NOTEXISTS"},
    ]
    users = await AsyncUser.batch_get(keys)

    assert len(users) == 1
    assert users[0].name == "Found"
