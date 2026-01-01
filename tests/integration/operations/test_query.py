"""Integration tests for query operation."""

import pytest


@pytest.fixture
def populated_table(dynamo):
    """Create a table with test data for query tests."""
    items = [
        {"pk": "USER#1", "sk": "PROFILE", "name": "Alice", "status": "active"},
        {"pk": "USER#1", "sk": "ORDER#001", "total": 100, "status": "shipped"},
        {"pk": "USER#1", "sk": "ORDER#002", "total": 200, "status": "pending"},
        {"pk": "USER#1", "sk": "ORDER#003", "total": 50, "status": "shipped"},
        {"pk": "USER#2", "sk": "PROFILE", "name": "Bob", "status": "inactive"},
        {"pk": "USER#2", "sk": "ORDER#001", "total": 75, "status": "shipped"},
    ]
    for item in items:
        dynamo.put_item("test_table", item)
    return dynamo


def test_query_by_partition_key(populated_table):
    """Test querying items by partition key only."""
    dynamo = populated_table

    count = 0
    for item in dynamo.query(
        "test_table",
        key_condition_expression="#pk = :pk",
        expression_attribute_names={"#pk": "pk"},
        expression_attribute_values={":pk": "USER#1"},
    ):
        assert item["pk"] == "USER#1"
        count += 1

    assert count == 4


def test_query_with_sort_key_begins_with(populated_table):
    """Test querying with begins_with on sort key."""
    dynamo = populated_table

    count = 0
    for item in dynamo.query(
        "test_table",
        key_condition_expression="#pk = :pk AND begins_with(#sk, :prefix)",
        expression_attribute_names={"#pk": "pk", "#sk": "sk"},
        expression_attribute_values={":pk": "USER#1", ":prefix": "ORDER#"},
    ):
        assert item["sk"].startswith("ORDER#")
        count += 1

    assert count == 3


def test_query_with_filter_expression(populated_table):
    """Test querying with a filter expression."""
    dynamo = populated_table

    count = 0
    for item in dynamo.query(
        "test_table",
        key_condition_expression="#pk = :pk",
        filter_expression="#status = :status",
        expression_attribute_names={"#pk": "pk", "#status": "status"},
        expression_attribute_values={":pk": "USER#1", ":status": "shipped"},
    ):
        assert item["status"] == "shipped"
        count += 1

    assert count == 2


def test_query_with_limit(populated_table):
    """Test querying with a limit per page."""
    dynamo = populated_table

    count = 0
    for _ in dynamo.query(
        "test_table",
        key_condition_expression="#pk = :pk",
        expression_attribute_names={"#pk": "pk"},
        expression_attribute_values={":pk": "USER#1"},
        limit=2,
    ):
        count += 1

    # Auto-pagination fetches all 4 items
    assert count == 4


def test_query_descending_order(populated_table):
    """Test querying in descending order."""
    dynamo = populated_table

    asc_keys = []
    for item in dynamo.query(
        "test_table",
        key_condition_expression="#pk = :pk AND begins_with(#sk, :prefix)",
        expression_attribute_names={"#pk": "pk", "#sk": "sk"},
        expression_attribute_values={":pk": "USER#1", ":prefix": "ORDER#"},
        scan_index_forward=True,
    ):
        asc_keys.append(item["sk"])

    desc_keys = []
    for item in dynamo.query(
        "test_table",
        key_condition_expression="#pk = :pk AND begins_with(#sk, :prefix)",
        expression_attribute_names={"#pk": "pk", "#sk": "sk"},
        expression_attribute_values={":pk": "USER#1", ":prefix": "ORDER#"},
        scan_index_forward=False,
    ):
        desc_keys.append(item["sk"])

    assert asc_keys == list(reversed(desc_keys))


def test_query_empty_result(populated_table):
    """Test querying with no matching items."""
    dynamo = populated_table

    results = dynamo.query(
        "test_table",
        key_condition_expression="#pk = :pk",
        expression_attribute_names={"#pk": "pk"},
        expression_attribute_values={":pk": "NONEXISTENT"},
    )

    count = 0
    for _ in results:
        count += 1

    assert count == 0
    assert results.last_evaluated_key is None


def test_query_result_has_last_evaluated_key(populated_table):
    """Test that query result has last_evaluated_key attribute."""
    dynamo = populated_table

    result = dynamo.query(
        "test_table",
        key_condition_expression="#pk = :pk",
        expression_attribute_names={"#pk": "pk"},
        expression_attribute_values={":pk": "USER#1"},
    )

    assert hasattr(result, "last_evaluated_key")

    for _ in result:
        pass

    # After consuming all, no more pages
    assert result.last_evaluated_key is None


@pytest.fixture
def large_table(dynamo):
    """Create a table with many items for pagination tests."""
    for i in range(15):
        dynamo.put_item(
            "test_table",
            {"pk": "USER#LARGE", "sk": f"ITEM#{i:03d}", "value": i},
        )
    return dynamo


def test_query_automatic_pagination(large_table):
    """Test that iterator automatically paginates through all results."""
    dynamo = large_table

    sort_keys = []
    for item in dynamo.query(
        "test_table",
        key_condition_expression="#pk = :pk",
        expression_attribute_names={"#pk": "pk"},
        expression_attribute_values={":pk": "USER#LARGE"},
        limit=4,
    ):
        sort_keys.append(item["sk"])

    assert len(sort_keys) == 15
    assert sort_keys == sorted(sort_keys)


def test_query_manual_pagination(large_table):
    """Test manual pagination using last_evaluated_key."""
    dynamo = large_table

    all_items = []

    # First page - consume only 4 items
    results = dynamo.query(
        "test_table",
        key_condition_expression="#pk = :pk",
        expression_attribute_names={"#pk": "pk"},
        expression_attribute_values={":pk": "USER#LARGE"},
        limit=4,
    )

    for item in results:
        all_items.append(item)
        if len(all_items) == 4:
            break

    assert results.last_evaluated_key is not None

    # Continue from where we left off
    for item in dynamo.query(
        "test_table",
        key_condition_expression="#pk = :pk",
        expression_attribute_names={"#pk": "pk"},
        expression_attribute_values={":pk": "USER#LARGE"},
        limit=4,
        last_evaluated_key=results.last_evaluated_key,
    ):
        all_items.append(item)

    assert len(all_items) == 15


def test_query_eventually_consistent(populated_table):
    """Test query with eventually consistent read (default)."""
    dynamo = populated_table

    count = 0
    for item in dynamo.query(
        "test_table",
        key_condition_expression="#pk = :pk",
        expression_attribute_names={"#pk": "pk"},
        expression_attribute_values={":pk": "USER#1"},
    ):
        assert item["pk"] == "USER#1"
        count += 1

    assert count == 4


def test_query_strongly_consistent(populated_table):
    """Test query with strongly consistent read."""
    dynamo = populated_table

    count = 0
    for item in dynamo.query(
        "test_table",
        key_condition_expression="#pk = :pk",
        expression_attribute_names={"#pk": "pk"},
        expression_attribute_values={":pk": "USER#1"},
        consistent_read=True,
    ):
        assert item["pk"] == "USER#1"
        count += 1

    assert count == 4


def test_query_consistent_read_empty_result(populated_table):
    """Test query with consistent_read returns empty for non-existent partition."""
    dynamo = populated_table

    results = dynamo.query(
        "test_table",
        key_condition_expression="#pk = :pk",
        expression_attribute_names={"#pk": "pk"},
        expression_attribute_values={":pk": "NONEXISTENT"},
        consistent_read=True,
    )

    count = 0
    for _ in results:
        count += 1

    assert count == 0


def test_query_consistent_read_with_filter(populated_table):
    """Test query with consistent_read and filter expression."""
    dynamo = populated_table

    count = 0
    for item in dynamo.query(
        "test_table",
        key_condition_expression="#pk = :pk",
        filter_expression="#status = :status",
        expression_attribute_names={"#pk": "pk", "#status": "status"},
        expression_attribute_values={":pk": "USER#1", ":status": "shipped"},
        consistent_read=True,
    ):
        assert item["status"] == "shipped"
        count += 1

    assert count == 2
