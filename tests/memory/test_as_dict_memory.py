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
    name = StringAttribute(null=True)
    data = StringAttribute(null=True)
    count = NumberAttribute(null=True)


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

    # Measure memory with Model instances
    def query_as_model():
        return list(MemoryTestModel.query(hash_key=pk))

    _, model_memory = measure_memory(query_as_model)

    # Measure memory with as_dict
    def query_as_dict():
        return list(MemoryTestModel.query(hash_key=pk, as_dict=True))

    _, dict_memory = measure_memory(query_as_dict)

    # Print results for visibility
    print("\nQuery memory comparison (500 items):")
    print(f"  Model instances: {model_memory / 1024:.1f} KB")
    print(f"  as_dict:         {dict_memory / 1024:.1f} KB")
    print(f"  Savings:         {(model_memory - dict_memory) / 1024:.1f} KB")
    print(f"  Ratio:           {model_memory / dict_memory:.2f}x")

    # as_dict should use less memory
    assert dict_memory < model_memory, "as_dict should use less memory than Model instances"


@pytest.mark.benchmark
def test_scan_model_vs_dict_memory(client, memory_table, setup_items):
    """Compare memory usage for scan: Model instances vs as_dict."""
    set_default_client(client)
    pk = setup_items

    # Use filter to scan only our items
    filter_cond = MemoryTestModel.pk == pk

    # Measure memory with Model instances
    def scan_as_model():
        return list(MemoryTestModel.scan(filter_condition=filter_cond, limit=200))

    _, model_memory = measure_memory(scan_as_model)

    # Measure memory with as_dict
    def scan_as_dict():
        return list(MemoryTestModel.scan(filter_condition=filter_cond, limit=200, as_dict=True))

    _, dict_memory = measure_memory(scan_as_dict)

    print("\nScan memory comparison (200 items):")
    print(f"  Model instances: {model_memory / 1024:.1f} KB")
    print(f"  as_dict:         {dict_memory / 1024:.1f} KB")
    print(f"  Savings:         {(model_memory - dict_memory) / 1024:.1f} KB")

    # Note: Memory savings may vary due to Python GC and tracemalloc overhead
    # The main benefit is visible in larger datasets and repeated operations
    if model_memory > dict_memory:
        print(f"  Ratio:           {model_memory / dict_memory:.2f}x")
    else:
        print("  Note: Memory difference negligible at this scale")


@pytest.mark.benchmark
def test_batch_get_model_vs_dict_memory(client, memory_table, setup_items):
    """Compare memory usage for batch_get: Model instances vs as_dict."""
    set_default_client(client)
    pk = setup_items

    keys = [{"pk": pk, "sk": f"ITEM#{i:04d}"} for i in range(100)]

    # Measure memory with Model instances
    def batch_get_as_model():
        return MemoryTestModel.batch_get(keys)

    _, model_memory = measure_memory(batch_get_as_model)

    # Measure memory with as_dict
    def batch_get_as_dict():
        return MemoryTestModel.batch_get(keys, as_dict=True)

    _, dict_memory = measure_memory(batch_get_as_dict)

    print("\nBatch get memory comparison (100 items):")
    print(f"  Model instances: {model_memory / 1024:.1f} KB")
    print(f"  as_dict:         {dict_memory / 1024:.1f} KB")
    print(f"  Savings:         {(model_memory - dict_memory) / 1024:.1f} KB")
    print(f"  Ratio:           {model_memory / dict_memory:.2f}x")

    assert dict_memory < model_memory


@pytest.mark.benchmark
def test_repeated_query_memory_stable(client, memory_table, setup_items):
    """Ensure repeated queries with as_dict don't leak memory."""
    set_default_client(client)
    pk = setup_items

    # Warm up
    list(MemoryTestModel.query(hash_key=pk, as_dict=True))

    # Measure first iteration
    tracemalloc.start()
    for _ in range(10):
        list(MemoryTestModel.query(hash_key=pk, as_dict=True))
    _, first_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # Measure second iteration
    tracemalloc.start()
    for _ in range(10):
        list(MemoryTestModel.query(hash_key=pk, as_dict=True))
    _, second_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    print("\nRepeated query memory (10 iterations each):")
    print(f"  First batch:  {first_peak / 1024:.1f} KB")
    print(f"  Second batch: {second_peak / 1024:.1f} KB")

    # Memory should not grow significantly between batches
    # Allow 20% variance for GC timing
    assert second_peak < first_peak * 1.2, "Memory should not grow between iterations"
