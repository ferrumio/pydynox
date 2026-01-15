"""Memory tests for scan and count operations.

Tests scan/count in loops to detect memory leaks.
"""

import uuid

import pytest


@pytest.mark.benchmark
def test_scan_loop(client, memory_table):
    """Scan operations in a loop - should not leak memory."""
    pk = f"MEMORY#scan#{uuid.uuid4()}"

    # GIVEN items in the table
    for i in range(50):
        client.put_item(
            memory_table,
            {"pk": pk, "sk": f"ITEM#{i:04d}", "data": f"test data {i}"},
        )

    # WHEN scanning repeatedly in a loop
    for _ in range(50):
        results = client.scan(memory_table)
        list(results)  # Consume the iterator
    # THEN memory should not grow (no assertions - memory profiler checks this)


@pytest.mark.benchmark
def test_scan_with_filter_loop(client, memory_table):
    """Scan with filter in a loop - should not leak memory."""
    pk = f"MEMORY#scanfilter#{uuid.uuid4()}"

    # GIVEN items in the table
    for i in range(50):
        client.put_item(
            memory_table,
            {"pk": pk, "sk": f"ITEM#{i:04d}", "data": f"test data {i}"},
        )

    # WHEN scanning with filter repeatedly in a loop
    for _ in range(50):
        results = client.scan(
            memory_table,
            filter_expression="begins_with(pk, :prefix)",
            expression_attribute_values={":prefix": pk},
        )
        list(results)
    # THEN memory should not grow (no assertions - memory profiler checks this)


@pytest.mark.benchmark
def test_count_loop(client, memory_table):
    """Count operations in a loop - should not leak memory."""
    pk = f"MEMORY#count#{uuid.uuid4()}"

    # GIVEN items in the table
    for i in range(30):
        client.put_item(
            memory_table,
            {"pk": pk, "sk": f"ITEM#{i:04d}", "data": f"test data {i}"},
        )

    # WHEN counting repeatedly in a loop
    for _ in range(100):
        count, _ = client.count(memory_table)
        # THEN count should be positive
        assert count > 0


@pytest.mark.benchmark
def test_count_with_filter_loop(client, memory_table):
    """Count with filter in a loop - should not leak memory."""
    pk = f"MEMORY#countfilter#{uuid.uuid4()}"

    # GIVEN items in the table
    for i in range(30):
        client.put_item(
            memory_table,
            {"pk": pk, "sk": f"ITEM#{i:04d}", "data": f"test data {i}"},
        )

    # WHEN counting with filter repeatedly in a loop
    for _ in range(100):
        count, _ = client.count(
            memory_table,
            filter_expression="begins_with(pk, :prefix)",
            expression_attribute_values={":prefix": pk},
        )
        # THEN count should be non-negative
        assert count >= 0


@pytest.mark.benchmark
def test_scan_pagination_loop(client, memory_table):
    """Scan with pagination in a loop - should not leak memory."""
    pk = f"MEMORY#scanpage#{uuid.uuid4()}"

    # GIVEN items in the table
    for i in range(100):
        client.put_item(
            memory_table,
            {"pk": pk, "sk": f"ITEM#{i:04d}", "data": f"test data {i}"},
        )

    # WHEN scanning with small limit (triggers pagination) repeatedly
    for _ in range(30):
        results = client.scan(memory_table, limit=10)
        list(results)  # Consume all pages
    # THEN memory should not grow (no assertions - memory profiler checks this)
