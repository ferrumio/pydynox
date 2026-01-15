"""Memory tests for CRUD operations.

Tests put/get/delete in loops to detect memory leaks.
"""

import uuid

import pytest


@pytest.mark.benchmark
def test_put_item_loop(client, memory_table):
    """Put items in a loop - should not leak memory."""
    # WHEN putting items repeatedly in a loop
    for i in range(100):
        client.put_item(
            memory_table,
            {
                "pk": f"MEMORY#put#{uuid.uuid4()}",
                "sk": f"ITEM#{i}",
                "data": f"test data {i}" * 10,
            },
        )
    # THEN memory should not grow (no assertions - memory profiler checks this)


@pytest.mark.benchmark
def test_get_item_loop(client, memory_table):
    """Get items in a loop - should not leak memory."""
    pk = f"MEMORY#get#{uuid.uuid4()}"

    # GIVEN items in the table
    for i in range(50):
        client.put_item(
            memory_table,
            {"pk": pk, "sk": f"ITEM#{i}", "data": f"test data {i}"},
        )

    # WHEN getting items repeatedly in a loop
    for i in range(50):
        for j in range(50):
            client.get_item(memory_table, {"pk": pk, "sk": f"ITEM#{j}"})
    # THEN memory should not grow (no assertions - memory profiler checks this)


@pytest.mark.benchmark
def test_delete_item_loop(client, memory_table):
    """Delete items in a loop - should not leak memory."""
    pk = f"MEMORY#delete#{uuid.uuid4()}"

    # GIVEN items in the table
    for i in range(100):
        client.put_item(
            memory_table,
            {"pk": pk, "sk": f"ITEM#{i}", "data": f"test data {i}"},
        )

    # WHEN deleting items in a loop
    for i in range(100):
        client.delete_item(memory_table, {"pk": pk, "sk": f"ITEM#{i}"})
    # THEN memory should not grow (no assertions - memory profiler checks this)


@pytest.mark.benchmark
def test_put_get_delete_cycle(client, memory_table):
    """Full CRUD cycle - should not leak memory."""
    # WHEN running full CRUD cycle repeatedly
    for i in range(100):
        pk = f"MEMORY#cycle#{uuid.uuid4()}"
        sk = f"ITEM#{i}"

        # Put
        client.put_item(
            memory_table,
            {"pk": pk, "sk": sk, "data": f"test data {i}" * 5},
        )

        # Get
        item = client.get_item(memory_table, {"pk": pk, "sk": sk})
        # THEN item should exist after put
        assert item is not None

        # Delete
        client.delete_item(memory_table, {"pk": pk, "sk": sk})


@pytest.mark.benchmark
def test_query_loop(client, memory_table):
    """Query operations in a loop - should not leak memory."""
    pk = f"MEMORY#query#{uuid.uuid4()}"

    # GIVEN items in the table
    for i in range(50):
        client.put_item(
            memory_table,
            {"pk": pk, "sk": f"ITEM#{i:04d}", "data": f"test data {i}"},
        )

    # WHEN querying repeatedly in a loop
    for _ in range(50):
        results = client.query(
            memory_table,
            key_condition_expression="pk = :pk",
            expression_attribute_values={":pk": pk},
        )
        list(results)  # Consume the iterator
    # THEN memory should not grow (no assertions - memory profiler checks this)
