"""Integration tests for operation metrics."""

from __future__ import annotations

import pytest
from pydynox import pydynox_core

OperationMetrics = pydynox_core.OperationMetrics


@pytest.mark.asyncio
async def test_put_item_returns_metrics(dynamo):
    """put_item returns OperationMetrics."""
    # WHEN we put an item
    metrics = await dynamo.put_item("test_table", {"pk": "USER#1", "sk": "PROFILE", "name": "John"})

    # THEN metrics are returned
    assert isinstance(metrics, OperationMetrics)
    assert metrics.duration_ms > 0


@pytest.mark.asyncio
async def test_get_item_returns_dict(dynamo):
    """get_item returns a plain dict."""
    # GIVEN an existing item
    await dynamo.put_item("test_table", {"pk": "USER#1", "sk": "PROFILE", "name": "John"})

    # WHEN we get the item
    item = await dynamo.get_item("test_table", {"pk": "USER#1", "sk": "PROFILE"})

    # THEN it works like a normal dict
    assert item["name"] == "John"
    assert item["pk"] == "USER#1"

    # AND metrics are available via client._last_metrics
    assert dynamo._last_metrics is not None
    assert isinstance(dynamo._last_metrics, OperationMetrics)
    assert dynamo._last_metrics.duration_ms > 0


@pytest.mark.asyncio
async def test_get_item_not_found_returns_none(dynamo):
    """get_item returns None when item not found."""
    item = await dynamo.get_item("test_table", {"pk": "MISSING", "sk": "MISSING"})

    assert item is None


@pytest.mark.asyncio
async def test_delete_item_returns_metrics(dynamo):
    """delete_item returns OperationMetrics."""
    await dynamo.put_item("test_table", {"pk": "USER#1", "sk": "PROFILE"})

    metrics = await dynamo.delete_item("test_table", {"pk": "USER#1", "sk": "PROFILE"})

    assert isinstance(metrics, OperationMetrics)
    assert metrics.duration_ms > 0


@pytest.mark.asyncio
async def test_update_item_returns_metrics(dynamo):
    """update_item returns OperationMetrics."""
    await dynamo.put_item("test_table", {"pk": "USER#1", "sk": "PROFILE", "count": 0})

    metrics = await dynamo.update_item(
        "test_table",
        {"pk": "USER#1", "sk": "PROFILE"},
        updates={"count": 5},
    )

    assert isinstance(metrics, OperationMetrics)
    assert metrics.duration_ms > 0


@pytest.mark.asyncio
async def test_query_result_has_last_evaluated_key(dynamo):
    """QueryResult exposes last_evaluated_key after iteration."""
    # GIVEN items in the table
    for i in range(3):
        await dynamo.put_item("test_table", {"pk": "ORG#1", "sk": f"USER#{i}", "name": f"User {i}"})

    # WHEN we query and iterate
    result = dynamo.query(
        "test_table",
        key_condition_expression="#pk = :pk",
        expression_attribute_names={"#pk": "pk"},
        expression_attribute_values={":pk": "ORG#1"},
    )
    items = [item async for item in result]

    # THEN all items are returned
    assert len(items) == 3

    # AND last_evaluated_key is None when all results fetched
    assert result.last_evaluated_key is None


@pytest.mark.asyncio
async def test_get_item_dict_is_mutable(dynamo):
    """Returned dict can be modified like a normal dict."""
    await dynamo.put_item("test_table", {"pk": "USER#1", "sk": "PROFILE", "name": "John"})

    item = await dynamo.get_item("test_table", {"pk": "USER#1", "sk": "PROFILE"})

    # Can modify
    item["name"] = "Jane"
    item["new_field"] = "value"

    assert item["name"] == "Jane"
    assert item["new_field"] == "value"
