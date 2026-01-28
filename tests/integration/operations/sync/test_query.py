"""Sync integration tests for query operation."""

import pytest


@pytest.fixture
def populated_table(dynamo):
    """Create a table with test data for query tests."""
    items = [
        {"pk": "SYNC_USER#1", "sk": "PROFILE", "name": "Alice", "status": "active"},
        {"pk": "SYNC_USER#1", "sk": "ORDER#001", "total": 100, "status": "shipped"},
        {"pk": "SYNC_USER#1", "sk": "ORDER#002", "total": 200, "status": "pending"},
        {"pk": "SYNC_USER#1", "sk": "ORDER#003", "total": 50, "status": "shipped"},
        {"pk": "SYNC_USER#2", "sk": "PROFILE", "name": "Bob", "status": "inactive"},
        {"pk": "SYNC_USER#2", "sk": "ORDER#001", "total": 75, "status": "shipped"},
    ]
    for item in items:
        dynamo.sync_put_item("test_table", item)
    return dynamo


def test_sync_query_by_partition_key(populated_table):
    """Test sync querying items by partition key only."""
    # GIVEN a populated table
    dynamo = populated_table

    # WHEN querying by partition key
    count = 0
    for item in dynamo.sync_query(
        "test_table",
        key_condition_expression="#pk = :pk",
        expression_attribute_names={"#pk": "pk"},
        expression_attribute_values={":pk": "SYNC_USER#1"},
    ):
        assert item["pk"] == "SYNC_USER#1"
        count += 1

    # THEN all items with that pk are returned
    assert count == 4


def test_sync_query_with_sort_key_begins_with(populated_table):
    """Test sync querying with begins_with on sort key."""
    # GIVEN a populated table
    dynamo = populated_table

    # WHEN querying with begins_with on sk
    count = 0
    for item in dynamo.sync_query(
        "test_table",
        key_condition_expression="#pk = :pk AND begins_with(#sk, :prefix)",
        expression_attribute_names={"#pk": "pk", "#sk": "sk"},
        expression_attribute_values={":pk": "SYNC_USER#1", ":prefix": "ORDER#"},
    ):
        assert item["sk"].startswith("ORDER#")
        count += 1

    # THEN only matching items are returned
    assert count == 3


def test_sync_query_with_filter_expression(populated_table):
    """Test sync querying with a filter expression."""
    # GIVEN a populated table
    dynamo = populated_table

    # WHEN querying with a filter
    count = 0
    for item in dynamo.sync_query(
        "test_table",
        key_condition_expression="#pk = :pk",
        filter_expression="#status = :status",
        expression_attribute_names={"#pk": "pk", "#status": "status"},
        expression_attribute_values={":pk": "SYNC_USER#1", ":status": "shipped"},
    ):
        assert item["status"] == "shipped"
        count += 1

    # THEN only filtered items are returned
    assert count == 2


def test_sync_query_with_limit(populated_table):
    """Test sync querying with a limit returns exactly that many items."""
    # GIVEN a populated table with 4 items for SYNC_USER#1
    dynamo = populated_table

    # WHEN querying with limit=2
    count = 0
    for _ in dynamo.sync_query(
        "test_table",
        key_condition_expression="#pk = :pk",
        expression_attribute_names={"#pk": "pk"},
        expression_attribute_values={":pk": "SYNC_USER#1"},
        limit=2,
    ):
        count += 1

    # THEN exactly 2 items are returned (limit is total, not per-page)
    assert count == 2


def test_sync_query_descending_order(populated_table):
    """Test sync querying in descending order."""
    # GIVEN a populated table
    dynamo = populated_table

    # WHEN querying in ascending order
    asc_keys = []
    for item in dynamo.sync_query(
        "test_table",
        key_condition_expression="#pk = :pk AND begins_with(#sk, :prefix)",
        expression_attribute_names={"#pk": "pk", "#sk": "sk"},
        expression_attribute_values={":pk": "SYNC_USER#1", ":prefix": "ORDER#"},
        scan_index_forward=True,
    ):
        asc_keys.append(item["sk"])

    # AND querying in descending order
    desc_keys = []
    for item in dynamo.sync_query(
        "test_table",
        key_condition_expression="#pk = :pk AND begins_with(#sk, :prefix)",
        expression_attribute_names={"#pk": "pk", "#sk": "sk"},
        expression_attribute_values={":pk": "SYNC_USER#1", ":prefix": "ORDER#"},
        scan_index_forward=False,
    ):
        desc_keys.append(item["sk"])

    # THEN orders are reversed
    assert asc_keys == list(reversed(desc_keys))


def test_sync_query_empty_result(populated_table):
    """Test sync querying with no matching items."""
    # GIVEN a populated table
    dynamo = populated_table

    # WHEN querying for non-existent partition
    results = dynamo.sync_query(
        "test_table",
        key_condition_expression="#pk = :pk",
        expression_attribute_names={"#pk": "pk"},
        expression_attribute_values={":pk": "NONEXISTENT"},
    )

    count = 0
    for _ in results:
        count += 1

    # THEN no items are returned
    assert count == 0
    assert results.last_evaluated_key is None


def test_sync_query_result_has_last_evaluated_key(populated_table):
    """Test that sync query result has last_evaluated_key attribute."""
    # GIVEN a populated table
    dynamo = populated_table

    # WHEN querying
    result = dynamo.sync_query(
        "test_table",
        key_condition_expression="#pk = :pk",
        expression_attribute_names={"#pk": "pk"},
        expression_attribute_values={":pk": "SYNC_USER#1"},
    )

    # THEN result has last_evaluated_key attribute
    assert hasattr(result, "last_evaluated_key")

    for _ in result:
        pass

    # AND after consuming all, no more pages
    assert result.last_evaluated_key is None


@pytest.fixture
def large_table(dynamo):
    """Create a table with many items for pagination tests."""
    for i in range(15):
        dynamo.sync_put_item(
            "test_table",
            {"pk": "SYNC_USER#LARGE", "sk": f"ITEM#{i:03d}", "value": i},
        )
    return dynamo


def test_sync_query_automatic_pagination(large_table):
    """Test that sync iterator automatically paginates when no limit is set."""
    # GIVEN a table with 15 items
    dynamo = large_table

    # WHEN querying without limit
    sort_keys = []
    for item in dynamo.sync_query(
        "test_table",
        key_condition_expression="#pk = :pk",
        expression_attribute_names={"#pk": "pk"},
        expression_attribute_values={":pk": "SYNC_USER#LARGE"},
    ):
        sort_keys.append(item["sk"])

    # THEN all 15 items are returned via auto-pagination
    assert len(sort_keys) == 15
    assert sort_keys == sorted(sort_keys)


def test_sync_query_manual_pagination(large_table):
    """Test sync manual pagination using last_evaluated_key."""
    # GIVEN a table with 15 items
    dynamo = large_table
    all_items = []

    # WHEN getting first page using page_size=4
    results = dynamo.sync_query(
        "test_table",
        key_condition_expression="#pk = :pk",
        expression_attribute_names={"#pk": "pk"},
        expression_attribute_values={":pk": "SYNC_USER#LARGE"},
        page_size=4,
    )

    for item in results:
        all_items.append(item)
        if len(all_items) == 4:
            break

    # THEN there's a next page
    assert results.last_evaluated_key is not None

    # AND continuing from last_evaluated_key gets remaining items
    for item in dynamo.sync_query(
        "test_table",
        key_condition_expression="#pk = :pk",
        expression_attribute_names={"#pk": "pk"},
        expression_attribute_values={":pk": "SYNC_USER#LARGE"},
        last_evaluated_key=results.last_evaluated_key,
    ):
        all_items.append(item)

    assert len(all_items) == 15


def test_sync_query_eventually_consistent(populated_table):
    """Test sync query with eventually consistent read (default)."""
    # GIVEN a populated table
    dynamo = populated_table

    # WHEN querying with default consistency
    count = 0
    for item in dynamo.sync_query(
        "test_table",
        key_condition_expression="#pk = :pk",
        expression_attribute_names={"#pk": "pk"},
        expression_attribute_values={":pk": "SYNC_USER#1"},
    ):
        assert item["pk"] == "SYNC_USER#1"
        count += 1

    # THEN all items are returned
    assert count == 4


def test_sync_query_strongly_consistent(populated_table):
    """Test sync query with strongly consistent read."""
    # GIVEN a populated table
    dynamo = populated_table

    # WHEN querying with consistent_read=True
    count = 0
    for item in dynamo.sync_query(
        "test_table",
        key_condition_expression="#pk = :pk",
        expression_attribute_names={"#pk": "pk"},
        expression_attribute_values={":pk": "SYNC_USER#1"},
        consistent_read=True,
    ):
        assert item["pk"] == "SYNC_USER#1"
        count += 1

    # THEN all items are returned
    assert count == 4


def test_sync_query_consistent_read_empty_result(populated_table):
    """Test sync query with consistent_read returns empty for non-existent partition."""
    # GIVEN a populated table
    dynamo = populated_table

    # WHEN querying non-existent partition with consistent_read
    results = dynamo.sync_query(
        "test_table",
        key_condition_expression="#pk = :pk",
        expression_attribute_names={"#pk": "pk"},
        expression_attribute_values={":pk": "NONEXISTENT"},
        consistent_read=True,
    )

    count = 0
    for _ in results:
        count += 1

    # THEN no items are returned
    assert count == 0


def test_sync_query_consistent_read_with_filter(populated_table):
    """Test sync query with consistent_read and filter expression."""
    # GIVEN a populated table
    dynamo = populated_table

    # WHEN querying with consistent_read and filter
    count = 0
    for item in dynamo.sync_query(
        "test_table",
        key_condition_expression="#pk = :pk",
        filter_expression="#status = :status",
        expression_attribute_names={"#pk": "pk", "#status": "status"},
        expression_attribute_values={":pk": "SYNC_USER#1", ":status": "shipped"},
        consistent_read=True,
    ):
        assert item["status"] == "shipped"
        count += 1

    # THEN only filtered items are returned
    assert count == 2
