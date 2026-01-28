"""Memory tests comparing Model instances vs as_dict.

Tests memory usage difference between returning Model instances
and plain dicts from query/scan operations.
"""

import tracemalloc
import uuid

import pytest
from pydynox import Model, ModelConfig, set_default_client
from pydynox.attributes import NumberAttribute, StringAttribute


class MemoryTestModel(Model):
    model_config = ModelConfig(table="memory_test_table")
    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    name = StringAttribute()
    data = StringAttribute()
    count = NumberAttribute()


@pytest.fixture(scope="module")
def setup_items(client, memory_table):
    """Create test items for memory comparison."""
    set_default_client(client)
    pk = f"MEMORY#asdict#{uuid.uuid4()}"

    # Create 500 items for meaningful memory comparison
    for i in range(500):
        client.put_item(
            memory_table,
            {
                "pk": pk,
                "sk": f"ITEM#{i:04d}",
                "name": f"Test Item {i}",
                "data": f"Some data content for item {i}" * 5,
                "count": i,
            },
        )

    return pk


def measure_memory(func):
    """Measure peak memory usage of a function."""
    tracemalloc.start()
    result = func()
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return result, peak


@pytest.mark.benchmark
def test_query_model_vs_dict_memory(client, memory_table, setup_items):
    """Compare memory usage: Model instances vs as_dict."""
    set_default_client(client)
    pk = setup_items

    # WHEN querying as Model instances
    def query_as_model():
        return list(MemoryTestModel.query(hash_key=pk))

    _, model_memory = measure_memory(query_as_model)

    # WHEN querying as dicts
    def query_as_dict():
        return list(MemoryTestModel.query(hash_key=pk, as_dict=True))

    _, dict_memory = measure_memory(query_as_dict)

    # THEN print comparison results
    print("\nQuery memory comparison (500 items):")
    print(f"  Model instances: {model_memory / 1024:.1f} KB")
    print(f"  as_dict:         {dict_memory / 1024:.1f} KB")
    print(f"  Savings:         {(model_memory - dict_memory) / 1024:.1f} KB")
    print(f"  Ratio:           {model_memory / dict_memory:.2f}x")

    # THEN as_dict should use less memory
    assert dict_memory < model_memory, "as_dict should use less memory than Model instances"


@pytest.mark.benchmark
def test_scan_model_vs_dict_memory(client, memory_table, setup_items):
    """Compare memory usage for scan: Model instances vs as_dict."""
    set_default_client(client)
    pk = setup_items

    filter_cond = MemoryTestModel.pk == pk

    # WHEN scanning as Model instances
    def scan_as_model():
        return list(MemoryTestModel.scan(filter_condition=filter_cond, limit=200))

    _, model_memory = measure_memory(scan_as_model)

    # WHEN scanning as dicts
    def scan_as_dict():
        return list(MemoryTestModel.scan(filter_condition=filter_cond, limit=200, as_dict=True))

    _, dict_memory = measure_memory(scan_as_dict)

    # THEN print comparison results
    print("\nScan memory comparison (200 items):")
    print(f"  Model instances: {model_memory / 1024:.1f} KB")
    print(f"  as_dict:         {dict_memory / 1024:.1f} KB")
    print(f"  Savings:         {(model_memory - dict_memory) / 1024:.1f} KB")

    if model_memory > dict_memory:
        print(f"  Ratio:           {model_memory / dict_memory:.2f}x")
    else:
        print("  Note: Memory difference negligible at this scale")


@pytest.mark.benchmark
def test_batch_get_model_vs_dict_memory(client, memory_table, setup_items):
    """Compare memory usage for batch_get: Model instances vs as_dict."""
    set_default_client(client)
    pk = setup_items

    # GIVEN keys for 100 items
    keys = [{"pk": pk, "sk": f"ITEM#{i:04d}"} for i in range(100)]

    # WHEN batch getting as Model instances
    def batch_get_as_model():
        return MemoryTestModel.batch_get(keys)

    _, model_memory = measure_memory(batch_get_as_model)

    # WHEN batch getting as dicts
    def batch_get_as_dict():
        return MemoryTestModel.batch_get(keys, as_dict=True)

    _, dict_memory = measure_memory(batch_get_as_dict)

    # THEN print comparison results
    print("\nBatch get memory comparison (100 items):")
    print(f"  Model instances: {model_memory / 1024:.1f} KB")
    print(f"  as_dict:         {dict_memory / 1024:.1f} KB")
    print(f"  Savings:         {(model_memory - dict_memory) / 1024:.1f} KB")
    print(f"  Ratio:           {model_memory / dict_memory:.2f}x")

    # THEN as_dict should use less memory
    assert dict_memory < model_memory


@pytest.mark.benchmark
def test_repeated_query_memory_stable(client, memory_table, setup_items):
    """Ensure repeated queries with as_dict don't leak memory."""
    set_default_client(client)
    pk = setup_items

    # GIVEN a warm-up query to stabilize memory
    list(MemoryTestModel.query(hash_key=pk, as_dict=True))

    # WHEN measuring first batch of 10 queries
    tracemalloc.start()
    for _ in range(10):
        list(MemoryTestModel.query(hash_key=pk, as_dict=True))
    _, first_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # WHEN measuring second batch of 10 queries
    tracemalloc.start()
    for _ in range(10):
        list(MemoryTestModel.query(hash_key=pk, as_dict=True))
    _, second_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    print("\nRepeated query memory (10 iterations each):")
    print(f"  First batch:  {first_peak / 1024:.1f} KB")
    print(f"  Second batch: {second_peak / 1024:.1f} KB")

    # THEN memory should not grow between batches (allow 20% for GC timing)
    assert second_peak < first_peak * 1.2, "Memory should not grow between iterations"
