"""Tests for async CRUD operations."""

import asyncio

import pytest
from pydynox import DynamoDBClient, Model, ModelConfig, set_default_client
from pydynox.attributes import NumberAttribute, StringAttribute

TABLE_NAME = "async_test_users"


@pytest.fixture
def async_table(dynamo: DynamoDBClient):
    """Create a test table for async tests."""
    set_default_client(dynamo)
    if not dynamo.table_exists(TABLE_NAME):
        dynamo.create_table(
            TABLE_NAME,
            hash_key=("pk", "S"),
            range_key=("sk", "S"),
            wait=True,
        )
    yield dynamo


class AsyncUser(Model):
    model_config = ModelConfig(table=TABLE_NAME)
    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    name = StringAttribute()
    age = NumberAttribute(null=True)


# ========== Client async tests ==========


@pytest.mark.asyncio
async def test_async_put_and_get_item(async_table: DynamoDBClient):
    """Test async put_item and get_item."""
    # GIVEN an item to save
    item = {"pk": "USER#async1", "sk": "PROFILE", "name": "Async User", "age": 25}

    # WHEN we put the item
    metrics = await async_table.async_put_item(TABLE_NAME, item)

    # THEN metrics are returned
    assert metrics.duration_ms > 0

    # AND we can get the item back
    result = await async_table.async_get_item(TABLE_NAME, {"pk": "USER#async1", "sk": "PROFILE"})
    assert result is not None
    assert result["name"] == "Async User"
    assert result["age"] == 25


@pytest.mark.asyncio
async def test_async_update_item(async_table: DynamoDBClient):
    """Test async update_item."""
    # GIVEN an existing item
    item = {"pk": "USER#async2", "sk": "PROFILE", "name": "Before Update"}
    await async_table.async_put_item(TABLE_NAME, item)

    # WHEN we update the item
    metrics = await async_table.async_update_item(
        TABLE_NAME,
        {"pk": "USER#async2", "sk": "PROFILE"},
        updates={"name": "After Update"},
    )

    # THEN metrics are returned
    assert metrics.duration_ms > 0

    # AND the update is applied
    result = await async_table.async_get_item(TABLE_NAME, {"pk": "USER#async2", "sk": "PROFILE"})
    assert result["name"] == "After Update"


@pytest.mark.asyncio
async def test_async_delete_item(async_table: DynamoDBClient):
    """Test async delete_item."""
    # GIVEN an existing item
    item = {"pk": "USER#async3", "sk": "PROFILE", "name": "To Delete"}
    await async_table.async_put_item(TABLE_NAME, item)

    # WHEN we delete the item
    metrics = await async_table.async_delete_item(
        TABLE_NAME, {"pk": "USER#async3", "sk": "PROFILE"}
    )

    # THEN metrics are returned
    assert metrics.duration_ms > 0

    # AND the item is gone
    result = await async_table.async_get_item(TABLE_NAME, {"pk": "USER#async3", "sk": "PROFILE"})
    assert result is None


@pytest.mark.asyncio
async def test_async_query(async_table: DynamoDBClient):
    """Test async query."""
    # GIVEN items with the same partition key
    for i in range(3):
        item = {"pk": "USER#query_async", "sk": f"ITEM#{i}", "name": f"Item {i}"}
        await async_table.async_put_item(TABLE_NAME, item)

    # WHEN we query by partition key
    items = []
    async for item in async_table.async_query(
        TABLE_NAME,
        key_condition_expression="#pk = :pk",
        expression_attribute_names={"#pk": "pk"},
        expression_attribute_values={":pk": "USER#query_async"},
    ):
        items.append(item)

    # THEN all items are returned
    assert len(items) == 3


@pytest.mark.asyncio
async def test_async_query_to_list(async_table: DynamoDBClient):
    """Test async query to_list()."""
    # GIVEN items with the same partition key
    for i in range(2):
        item = {"pk": "USER#list_async", "sk": f"ITEM#{i}", "name": f"Item {i}"}
        await async_table.async_put_item(TABLE_NAME, item)

    # WHEN we query with to_list()
    items = await async_table.async_query(
        TABLE_NAME,
        key_condition_expression="#pk = :pk",
        expression_attribute_names={"#pk": "pk"},
        expression_attribute_values={":pk": "USER#list_async"},
    ).to_list()

    # THEN all items are returned as a list
    assert len(items) == 2


# ========== Model async tests ==========


@pytest.mark.asyncio
async def test_model_async_save_and_get(async_table: DynamoDBClient):
    """Test Model.async_save() and Model.async_get()."""
    # GIVEN a model instance
    user = AsyncUser(pk="USER#model1", sk="PROFILE", name="Model User", age=30)

    # WHEN we save it
    await user.async_save()

    # THEN we can get it back
    loaded = await AsyncUser.async_get(pk="USER#model1", sk="PROFILE")
    assert loaded is not None
    assert loaded.name == "Model User"
    assert loaded.age == 30


@pytest.mark.asyncio
async def test_model_async_update(async_table: DynamoDBClient):
    """Test Model.async_update()."""
    # GIVEN a saved model
    user = AsyncUser(pk="USER#model2", sk="PROFILE", name="Before", age=20)
    await user.async_save()

    # WHEN we update it
    await user.async_update(name="After", age=21)

    # THEN the changes are persisted
    loaded = await AsyncUser.async_get(pk="USER#model2", sk="PROFILE")
    assert loaded.name == "After"
    assert loaded.age == 21


@pytest.mark.asyncio
async def test_model_async_delete(async_table: DynamoDBClient):
    """Test Model.async_delete()."""
    # GIVEN a saved model
    user = AsyncUser(pk="USER#model3", sk="PROFILE", name="To Delete")
    await user.async_save()

    # WHEN we delete it
    await user.async_delete()

    # THEN it's gone
    loaded = await AsyncUser.async_get(pk="USER#model3", sk="PROFILE")
    assert loaded is None


# ========== Concurrent operations ==========


@pytest.mark.asyncio
async def test_concurrent_gets(async_table: DynamoDBClient):
    """Test running multiple async gets concurrently."""
    # GIVEN multiple items in the table
    for i in range(5):
        item = {"pk": f"USER#concurrent{i}", "sk": "PROFILE", "name": f"User {i}"}
        await async_table.async_put_item(TABLE_NAME, item)

    # WHEN we get all concurrently
    results = await asyncio.gather(
        async_table.async_get_item(TABLE_NAME, {"pk": "USER#concurrent0", "sk": "PROFILE"}),
        async_table.async_get_item(TABLE_NAME, {"pk": "USER#concurrent1", "sk": "PROFILE"}),
        async_table.async_get_item(TABLE_NAME, {"pk": "USER#concurrent2", "sk": "PROFILE"}),
        async_table.async_get_item(TABLE_NAME, {"pk": "USER#concurrent3", "sk": "PROFILE"}),
        async_table.async_get_item(TABLE_NAME, {"pk": "USER#concurrent4", "sk": "PROFILE"}),
    )

    # THEN all results are returned correctly
    assert len(results) == 5
    for i, result in enumerate(results):
        assert result is not None
        assert result["name"] == f"User {i}"


@pytest.mark.asyncio
async def test_concurrent_model_gets(async_table: DynamoDBClient):
    """Test running multiple Model.async_get() concurrently."""
    # GIVEN multiple saved models
    for i in range(3):
        user = AsyncUser(pk=f"USER#mconc{i}", sk="PROFILE", name=f"User {i}")
        await user.async_save()

    # WHEN we get all concurrently
    results = await asyncio.gather(
        AsyncUser.async_get(pk="USER#mconc0", sk="PROFILE"),
        AsyncUser.async_get(pk="USER#mconc1", sk="PROFILE"),
        AsyncUser.async_get(pk="USER#mconc2", sk="PROFILE"),
    )

    # THEN all results are returned correctly
    assert len(results) == 3
    for i, user in enumerate(results):
        assert user is not None
        assert user.name == f"User {i}"
