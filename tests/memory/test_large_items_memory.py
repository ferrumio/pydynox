"""Memory tests for large items near 400KB limit.

Tests operations with items close to DynamoDB's 400KB limit
to detect memory issues with large allocations.
"""

import uuid

import pytest
from pydynox.size import DYNAMODB_MAX_ITEM_SIZE, calculate_item_size


def create_large_item(pk: str, sk: str, target_size_kb: int) -> dict:
    """Create an item close to target size in KB."""
    # Start with base item
    item = {"pk": pk, "sk": sk, "data": ""}

    # Calculate how much data we need
    base_size = calculate_item_size(item).bytes
    target_bytes = target_size_kb * 1024
    data_size = target_bytes - base_size

    if data_size > 0:
        item["data"] = "x" * data_size

    return item


@pytest.mark.benchmark
def test_put_large_items_300kb(client, memory_table):
    """Put 300KB items - should not leak memory."""
    # WHEN putting 300KB items in a loop
    for i in range(10):
        pk = f"MEMORY#large300#{uuid.uuid4()}"
        item = create_large_item(pk, f"ITEM#{i}", 300)

        client.put_item(memory_table, item)
    # THEN memory should not grow (no assertions - memory profiler checks this)


@pytest.mark.benchmark
def test_put_large_items_350kb(client, memory_table):
    """Put 350KB items (close to limit) - should not leak memory."""
    # WHEN putting 350KB items (near DynamoDB limit) in a loop
    for i in range(10):
        pk = f"MEMORY#large350#{uuid.uuid4()}"
        item = create_large_item(pk, f"ITEM#{i}", 350)

        client.put_item(memory_table, item)
    # THEN memory should not grow (no assertions - memory profiler checks this)


@pytest.mark.benchmark
def test_get_large_items(client, memory_table):
    """Get large items - should not leak memory."""
    pk = f"MEMORY#get_large#{uuid.uuid4()}"

    # GIVEN large items (300KB each) in the table
    for i in range(5):
        item = create_large_item(pk, f"ITEM#{i}", 300)
        client.put_item(memory_table, item)

    # WHEN getting items repeatedly in a loop
    for _ in range(20):
        for i in range(5):
            result = client.get_item(memory_table, {"pk": pk, "sk": f"ITEM#{i}"})
            # THEN each item should be returned with full data
            assert result is not None
            assert len(result["data"]) > 200000


@pytest.mark.benchmark
def test_query_large_items(client, memory_table):
    """Query large items - should not leak memory."""
    pk = f"MEMORY#query_large#{uuid.uuid4()}"

    # GIVEN large items (200KB each) in the table
    for i in range(5):
        item = create_large_item(pk, f"ITEM#{i:04d}", 200)
        client.put_item(memory_table, item)

    # WHEN querying repeatedly in a loop
    for _ in range(20):
        results = list(
            client.query(
                memory_table,
                key_condition_expression="pk = :pk",
                expression_attribute_values={":pk": pk},
            )
        )
        # THEN all items should be returned each time
        assert len(results) == 5


@pytest.mark.benchmark
def test_size_calculation_large_items():
    """Calculate size of large items - should not leak memory."""
    # WHEN calculating size of items with varying sizes in a loop
    for _ in range(100):
        for size_kb in [100, 200, 300, 350]:
            item = create_large_item("pk", "sk", size_kb)
            size = calculate_item_size(item)

            # THEN size should be close to target and under DynamoDB limit
            assert size.bytes > (size_kb - 10) * 1024
            assert size.bytes < DYNAMODB_MAX_ITEM_SIZE


@pytest.mark.benchmark
def test_large_item_with_many_attributes(client, memory_table):
    """Large item with many attributes - should not leak memory."""
    # WHEN putting items with 100 attributes each in a loop
    for i in range(20):
        pk = f"MEMORY#many_attrs#{uuid.uuid4()}"

        item = {"pk": pk, "sk": f"ITEM#{i}"}
        for j in range(100):
            item[f"attr_{j}"] = f"value_{j}" * 100

        client.put_item(memory_table, item)
    # THEN memory should not grow (no assertions - memory profiler checks this)
