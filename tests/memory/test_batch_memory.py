"""Memory tests for batch operations.

Tests batch write/get with 100+ items to detect memory leaks
from large allocations.
"""

import uuid

import pytest


@pytest.mark.benchmark
def test_batch_write_100_items(client, memory_table):
    """Batch write 100 items - should not leak memory."""
    pk = f"MEMORY#batch_write#{uuid.uuid4()}"

    # GIVEN 100 items to write
    items = [{"pk": pk, "sk": f"ITEM#{i:04d}", "data": f"batch data {i}" * 10} for i in range(100)]

    # WHEN batch writing
    client.batch_write(memory_table, items)
    # THEN memory should not grow (no assertions - memory profiler checks this)


@pytest.mark.benchmark
def test_batch_write_multiple_batches(client, memory_table):
    """Multiple batch writes - should not leak memory."""
    # WHEN batch writing multiple times in a loop
    for batch_num in range(10):
        pk = f"MEMORY#multi_batch#{uuid.uuid4()}"

        items = [
            {"pk": pk, "sk": f"ITEM#{i:04d}", "data": f"batch {batch_num} data {i}"}
            for i in range(100)
        ]

        client.batch_write(memory_table, items)
    # THEN memory should not grow (no assertions - memory profiler checks this)


@pytest.mark.benchmark
def test_batch_get_100_items(client, memory_table):
    """Batch get 100 items - should not leak memory."""
    pk = f"MEMORY#batch_get#{uuid.uuid4()}"

    # GIVEN 100 items in the table
    items = [{"pk": pk, "sk": f"ITEM#{i:04d}", "data": f"batch data {i}"} for i in range(100)]
    client.batch_write(memory_table, items)

    # WHEN batch getting all items
    keys = [{"pk": pk, "sk": f"ITEM#{i:04d}"} for i in range(100)]
    results = client.batch_get(memory_table, keys)

    # THEN all items should be returned
    assert len(results) == 100


@pytest.mark.benchmark
def test_batch_get_multiple_rounds(client, memory_table):
    """Multiple batch gets - should not leak memory."""
    pk = f"MEMORY#batch_get_multi#{uuid.uuid4()}"

    # GIVEN 100 items in the table
    items = [{"pk": pk, "sk": f"ITEM#{i:04d}", "data": f"batch data {i}"} for i in range(100)]
    client.batch_write(memory_table, items)

    keys = [{"pk": pk, "sk": f"ITEM#{i:04d}"} for i in range(100)]

    # WHEN batch getting multiple times in a loop
    for _ in range(20):
        results = client.batch_get(memory_table, keys)
        # THEN all items should be returned each time
        assert len(results) == 100


@pytest.mark.benchmark
def test_batch_write_large_items(client, memory_table):
    """Batch write with larger items - should not leak memory."""
    pk = f"MEMORY#batch_large#{uuid.uuid4()}"

    # GIVEN 25 items of ~10KB each (to stay under batch limits)
    items = [{"pk": pk, "sk": f"ITEM#{i:04d}", "data": "x" * 10000} for i in range(25)]

    # WHEN batch writing multiple times in a loop
    for _ in range(10):
        client.batch_write(memory_table, items)
    # THEN memory should not grow (no assertions - memory profiler checks this)
