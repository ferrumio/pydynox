"""Integration tests for operation metrics."""

from __future__ import annotations

from pydynox import pydynox_core

OperationMetrics = pydynox_core.OperationMetrics


def test_put_item_returns_metrics(dynamo):
    """put_item returns OperationMetrics."""
    metrics = dynamo.put_item("test_table", {"pk": "USER#1", "sk": "PROFILE", "name": "John"})

    assert isinstance(metrics, OperationMetrics)
    assert metrics.duration_ms > 0


def test_get_item_returns_dict_with_metrics(dynamo):
    """get_item returns a dict with .metrics attribute."""
    dynamo.put_item("test_table", {"pk": "USER#1", "sk": "PROFILE", "name": "John"})

    item = dynamo.get_item("test_table", {"pk": "USER#1", "sk": "PROFILE"})

    # Works like a normal dict
    assert item["name"] == "John"
    assert item["pk"] == "USER#1"

    # Has metrics
    assert hasattr(item, "metrics")
    assert isinstance(item.metrics, OperationMetrics)
    assert item.metrics.duration_ms > 0


def test_get_item_not_found_returns_none(dynamo):
    """get_item returns None when item not found."""
    item = dynamo.get_item("test_table", {"pk": "MISSING", "sk": "MISSING"})

    assert item is None


def test_delete_item_returns_metrics(dynamo):
    """delete_item returns OperationMetrics."""
    dynamo.put_item("test_table", {"pk": "USER#1", "sk": "PROFILE"})

    metrics = dynamo.delete_item("test_table", {"pk": "USER#1", "sk": "PROFILE"})

    assert isinstance(metrics, OperationMetrics)
    assert metrics.duration_ms > 0


def test_update_item_returns_metrics(dynamo):
    """update_item returns OperationMetrics."""
    dynamo.put_item("test_table", {"pk": "USER#1", "sk": "PROFILE", "count": 0})

    metrics = dynamo.update_item(
        "test_table",
        {"pk": "USER#1", "sk": "PROFILE"},
        updates={"count": 5},
    )

    assert isinstance(metrics, OperationMetrics)
    assert metrics.duration_ms > 0


def test_query_result_has_metrics(dynamo):
    """QueryResult exposes .metrics after iteration."""
    # Setup data
    for i in range(3):
        dynamo.put_item("test_table", {"pk": "ORG#1", "sk": f"USER#{i}", "name": f"User {i}"})

    # Query
    result = dynamo.query(
        "test_table",
        key_condition_expression="#pk = :pk",
        expression_attribute_names={"#pk": "pk"},
        expression_attribute_values={":pk": "ORG#1"},
    )

    # Iterate to trigger fetch
    items = list(result)
    assert len(items) == 3

    # Metrics available after fetch
    assert result.metrics is not None
    assert isinstance(result.metrics, OperationMetrics)
    assert result.metrics.duration_ms > 0


def test_query_metrics_has_items_count(dynamo):
    """Query metrics includes items_count."""
    for i in range(5):
        dynamo.put_item("test_table", {"pk": "ORG#2", "sk": f"USER#{i}"})

    result = dynamo.query(
        "test_table",
        key_condition_expression="#pk = :pk",
        expression_attribute_names={"#pk": "pk"},
        expression_attribute_values={":pk": "ORG#2"},
    )
    list(result)

    assert result.metrics.items_count == 5


def test_get_item_dict_is_mutable(dynamo):
    """Returned dict can be modified like a normal dict."""
    dynamo.put_item("test_table", {"pk": "USER#1", "sk": "PROFILE", "name": "John"})

    item = dynamo.get_item("test_table", {"pk": "USER#1", "sk": "PROFILE"})

    # Can modify
    item["name"] = "Jane"
    item["new_field"] = "value"

    assert item["name"] == "Jane"
    assert item["new_field"] == "value"

    # Metrics still accessible
    assert item.metrics.duration_ms > 0
