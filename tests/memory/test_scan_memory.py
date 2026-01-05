"""Memory tests for scan and count operations.

Tests scan/count in loops to detect memory leaks.
"""

import uuid

import pytest


@pytest.mark.benchmark
def test_scan_loop(client, memory_table):
    """Scan operations in a loop - should not leak memory."""
    pk = f"MEMORY#scan#{uuid.uuid4()}"

    # Setup: create items to scan
    for i in range(50):
        client.put_item(
            memory_table,
            {"pk": pk, "sk": f"ITEM#{i:04d}", "data": f"test data {i}"},
        )

    # Test: scan repeatedly
    for _ in range(50):
        results = client.scan(memory_table)
        list(results)  # Consume the iterator


@pytest.mark.benchmark
def test_scan_with_filter_loop(client, memory_table):
    """Scan with filter in a loop - should not leak memory."""
    pk = f"MEMORY#scanfilter#{uuid.uuid4()}"

    # Setup: create items
    for i in range(50):
        client.put_item(
            memory_table,
            {"pk": pk, "sk": f"ITEM#{i:04d}", "data": f"test data {i}"},
        )

    # Test: scan with filter repeatedly
    for _ in range(50):
        results = client.scan(
            memory_table,
            filter_expression="begins_with(pk, :prefix)",
            expression_attribute_values={":prefix": pk},
        )
        list(results)


@pytest.mark.benchmark
def test_count_loop(client, memory_table):
    """Count operations in a loop - should not leak memory."""
    pk = f"MEMORY#count#{uuid.uuid4()}"

    # Setup: create items to count
    for i in range(30):
        client.put_item(
            memory_table,
            {"pk": pk, "sk": f"ITEM#{i:04d}", "data": f"test data {i}"},
        )

    # Test: count repeatedly
    for _ in range(100):
        count, _ = client.count(memory_table)
        assert count > 0


@pytest.mark.benchmark
def test_count_with_filter_loop(client, memory_table):
    """Count with filter in a loop - should not leak memory."""
    pk = f"MEMORY#countfilter#{uuid.uuid4()}"

    # Setup: create items
    for i in range(30):
        client.put_item(
            memory_table,
            {"pk": pk, "sk": f"ITEM#{i:04d}", "data": f"test data {i}"},
        )

    # Test: count with filter repeatedly
    for _ in range(100):
        count, _ = client.count(
            memory_table,
            filter_expression="begins_with(pk, :prefix)",
            expression_attribute_values={":prefix": pk},
        )
        assert count >= 0


@pytest.mark.benchmark
def test_scan_pagination_loop(client, memory_table):
    """Scan with pagination in a loop - should not leak memory."""
    pk = f"MEMORY#scanpage#{uuid.uuid4()}"

    # Setup: create items
    for i in range(100):
        client.put_item(
            memory_table,
            {"pk": pk, "sk": f"ITEM#{i:04d}", "data": f"test data {i}"},
        )

    # Test: scan with small limit repeatedly
    for _ in range(30):
        results = client.scan(memory_table, limit=10)
        list(results)  # Consume all pages
