"""Sync integration tests for scan operation."""

import pytest


@pytest.fixture
def scan_data(dynamo):
    """Create test data for scan tests."""
    items = [
        {"pk": "SYNC_SCAN#1", "sk": "ITEM#1", "name": "Alice", "status": "active"},
        {"pk": "SYNC_SCAN#2", "sk": "ITEM#2", "name": "Bob", "status": "active"},
        {"pk": "SYNC_SCAN#3", "sk": "ITEM#3", "name": "Charlie", "status": "inactive"},
        {"pk": "SYNC_SCAN#4", "sk": "ITEM#4", "name": "Diana", "status": "active"},
        {"pk": "SYNC_SCAN#5", "sk": "ITEM#5", "name": "Eve", "status": "inactive"},
    ]
    for item in items:
        dynamo.sync_put_item("test_table", item)
    return dynamo


def test_sync_scan_all_items(scan_data):
    """Test sync scan returns items."""
    dynamo = scan_data

    # WHEN we scan
    items = []
    for item in dynamo.sync_scan("test_table"):
        if item["pk"].startswith("SYNC_SCAN#"):
            items.append(item)

    # THEN items are returned
    assert len(items) >= 5


def test_sync_scan_with_filter(scan_data):
    """Test sync scan with filter expression."""
    dynamo = scan_data

    # WHEN we scan with filter
    items = []
    for item in dynamo.sync_scan(
        "test_table",
        filter_expression="#s = :status AND begins_with(#pk, :prefix)",
        expression_attribute_names={"#s": "status", "#pk": "pk"},
        expression_attribute_values={":status": "active", ":prefix": "SYNC_SCAN#"},
    ):
        items.append(item)

    # THEN only matching items are returned
    assert len(items) == 3
    for item in items:
        assert item["status"] == "active"


def test_sync_scan_with_limit(scan_data):
    """Test sync scan with limit."""
    dynamo = scan_data

    # WHEN we scan with limit
    items = []
    for item in dynamo.sync_scan("test_table", limit=2):
        items.append(item)

    # THEN only limited items are returned
    assert len(items) == 2


def test_sync_scan_empty_result(dynamo):
    """Test sync scan with filter that matches nothing."""
    # WHEN we scan with filter that matches nothing
    items = []
    for item in dynamo.sync_scan(
        "test_table",
        filter_expression="#pk = :pk",
        expression_attribute_names={"#pk": "pk"},
        expression_attribute_values={":pk": "NONEXISTENT_SCAN_KEY"},
    ):
        items.append(item)

    # THEN no items are returned
    assert len(items) == 0


def test_sync_scan_result_has_last_evaluated_key(scan_data):
    """Test that sync scan result has last_evaluated_key attribute."""
    dynamo = scan_data

    # WHEN scanning
    result = dynamo.sync_scan("test_table")

    # THEN result has last_evaluated_key attribute
    assert hasattr(result, "last_evaluated_key")

    for _ in result:
        pass

    # AND after consuming all, no more pages
    assert result.last_evaluated_key is None


def test_sync_scan_consistent_read(scan_data):
    """Test sync scan with consistent_read=True."""
    dynamo = scan_data

    # WHEN we scan with consistent_read
    items = []
    for item in dynamo.sync_scan(
        "test_table",
        filter_expression="begins_with(#pk, :prefix)",
        expression_attribute_names={"#pk": "pk"},
        expression_attribute_values={":prefix": "SYNC_SCAN#"},
        consistent_read=True,
    ):
        items.append(item)

    # THEN items are returned
    assert len(items) >= 5


def test_sync_scan_with_projection(scan_data):
    """Test sync scan with projection expression."""
    dynamo = scan_data

    # WHEN we scan with projection
    items = []
    for item in dynamo.sync_scan(
        "test_table",
        filter_expression="begins_with(#pk, :prefix)",
        projection_expression="#pk, #sk, #n",
        expression_attribute_names={"#pk": "pk", "#sk": "sk", "#n": "name"},
        expression_attribute_values={":prefix": "SYNC_SCAN#"},
    ):
        items.append(item)

    # THEN only projected attributes are returned
    assert len(items) >= 5
    for item in items:
        assert "pk" in item
        assert "sk" in item
        assert "name" in item
        # status should not be in result (projected out)
        assert "status" not in item
