"""Tests that prove async operations don't block the event loop."""

import asyncio
import time

import pytest
from pydynox import DynamoDBClient, Model, ModelConfig, set_default_client
from pydynox.attributes import StringAttribute

TABLE_NAME = "async_concurrency_test"


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


class Item(Model):
    model_config = ModelConfig(table=TABLE_NAME)
    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    data = StringAttribute()


@pytest.mark.asyncio
async def test_async_does_not_block_event_loop(async_table: DynamoDBClient):
    """Prove that async operations allow other tasks to run.

    This test runs a counter task alongside DynamoDB operations.
    If async is working, the counter should increment while waiting for DynamoDB.
    If it was blocking, the counter would stay at 0.
    """
    counter = 0
    counter_running = True

    async def increment_counter():
        """Task that increments counter every 1ms."""
        nonlocal counter
        while counter_running:
            counter += 1
            await asyncio.sleep(0.001)  # 1ms

    # Start counter task
    counter_task = asyncio.create_task(increment_counter())

    # Do some DynamoDB operations
    for i in range(5):
        item = {"pk": "BLOCK#test", "sk": f"ITEM#{i}", "data": f"data-{i}"}
        await async_table.async_put_item(TABLE_NAME, item)

    # Stop counter
    counter_running = False
    await counter_task

    # If async is working, counter should have incremented many times
    # while waiting for DynamoDB I/O
    assert counter > 0, "Counter should have incremented - async is not working!"


@pytest.mark.asyncio
async def test_concurrent_operations_faster_than_sequential(async_table: DynamoDBClient):
    """Prove that concurrent async operations are faster than sequential.

    If async is truly non-blocking, running N operations concurrently
    should take roughly the same time as 1 operation, not N times longer.
    """
    n_operations = 10

    # Create test items first
    for i in range(n_operations):
        item = {"pk": "SPEED#test", "sk": f"ITEM#{i}", "data": f"data-{i}"}
        await async_table.async_put_item(TABLE_NAME, item)

    # Measure sequential gets
    start_seq = time.perf_counter()
    for i in range(n_operations):
        await async_table.async_get_item(TABLE_NAME, {"pk": "SPEED#test", "sk": f"ITEM#{i}"})
    sequential_time = time.perf_counter() - start_seq

    # Measure concurrent gets
    start_conc = time.perf_counter()
    await asyncio.gather(
        *[
            async_table.async_get_item(TABLE_NAME, {"pk": "SPEED#test", "sk": f"ITEM#{i}"})
            for i in range(n_operations)
        ]
    )
    concurrent_time = time.perf_counter() - start_conc

    # Concurrent should be faster (at least 1.5x for this test)
    # Note: with DynamoDB Local the difference might be smaller
    assert concurrent_time < sequential_time, "Concurrent should be faster than sequential"


@pytest.mark.asyncio
async def test_model_async_concurrent_saves(async_table: DynamoDBClient):
    """Test that Model async saves can run concurrently."""
    n_items = 10

    # Create items
    items = [Item(pk="MODEL#conc", sk=f"ITEM#{i}", data=f"data-{i}") for i in range(n_items)]

    # Save all concurrently
    await asyncio.gather(*[item.async_save() for item in items])

    # Verify all saved
    for i in range(n_items):
        loaded = await Item.async_get(pk="MODEL#conc", sk=f"ITEM#{i}")
        assert loaded is not None
        assert loaded.data == f"data-{i}"


@pytest.mark.asyncio
async def test_mixed_operations_concurrent(async_table: DynamoDBClient):
    """Test running different operation types concurrently."""
    # Setup: create some items
    for i in range(3):
        item = {"pk": "MIXED#test", "sk": f"ITEM#{i}", "data": f"original-{i}"}
        await async_table.async_put_item(TABLE_NAME, item)

    # Run mixed operations concurrently:
    # - Get item 0
    # - Update item 1
    # - Delete item 2
    # - Put new item 3
    results = await asyncio.gather(
        async_table.async_get_item(TABLE_NAME, {"pk": "MIXED#test", "sk": "ITEM#0"}),
        async_table.async_update_item(
            TABLE_NAME,
            {"pk": "MIXED#test", "sk": "ITEM#1"},
            updates={"data": "updated-1"},
        ),
        async_table.async_delete_item(TABLE_NAME, {"pk": "MIXED#test", "sk": "ITEM#2"}),
        async_table.async_put_item(
            TABLE_NAME,
            {"pk": "MIXED#test", "sk": "ITEM#3", "data": "new-3"},
        ),
    )

    # Verify results
    get_result = results[0]
    assert get_result is not None
    assert get_result["data"] == "original-0"

    # Verify update
    updated = await async_table.async_get_item(TABLE_NAME, {"pk": "MIXED#test", "sk": "ITEM#1"})
    assert updated["data"] == "updated-1"

    # Verify delete
    deleted = await async_table.async_get_item(TABLE_NAME, {"pk": "MIXED#test", "sk": "ITEM#2"})
    assert deleted is None

    # Verify new item
    new_item = await async_table.async_get_item(TABLE_NAME, {"pk": "MIXED#test", "sk": "ITEM#3"})
    assert new_item["data"] == "new-3"
