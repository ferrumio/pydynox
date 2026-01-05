"""Unit tests for OperationMetrics."""

from __future__ import annotations

import pytest
from pydynox import pydynox_core
from pydynox._internal._metrics import DictWithMetrics

OperationMetrics = pydynox_core.OperationMetrics


def test_operation_metrics_default():
    """OperationMetrics can be created with defaults."""
    m = OperationMetrics()
    assert m.duration_ms == 0.0
    assert m.consumed_rcu is None
    assert m.consumed_wcu is None
    assert m.request_id is None
    assert m.items_count is None
    assert m.scanned_count is None


def test_operation_metrics_with_duration():
    """OperationMetrics accepts duration_ms."""
    m = OperationMetrics(duration_ms=42.5)
    assert m.duration_ms == 42.5


def test_operation_metrics_repr():
    """OperationMetrics has a readable repr."""
    m = OperationMetrics(duration_ms=10.5)
    assert "duration_ms=10.50" in repr(m)


def test_dict_with_metrics_acts_like_dict():
    """DictWithMetrics works like a normal dict."""
    m = OperationMetrics(duration_ms=5.0)
    d = DictWithMetrics({"name": "John", "age": 30}, m)

    assert d["name"] == "John"
    assert d["age"] == 30
    assert len(d) == 2
    assert "name" in d
    assert list(d.keys()) == ["name", "age"]


def test_dict_with_metrics_has_metrics():
    """DictWithMetrics exposes .metrics attribute."""
    m = OperationMetrics(duration_ms=15.0)
    d = DictWithMetrics({"pk": "USER#1"}, m)

    assert d.metrics is m
    assert d.metrics.duration_ms == 15.0


def test_dict_with_metrics_is_dict_subclass():
    """DictWithMetrics is a dict subclass."""
    m = OperationMetrics()
    d = DictWithMetrics({}, m)

    assert isinstance(d, dict)


@pytest.mark.parametrize(
    "data",
    [
        pytest.param({}, id="empty"),
        pytest.param({"a": 1}, id="single"),
        pytest.param({"a": 1, "b": "two", "c": [1, 2, 3]}, id="mixed"),
    ],
)
def test_dict_with_metrics_preserves_data(data):
    """DictWithMetrics preserves all dict data."""
    m = OperationMetrics()
    d = DictWithMetrics(data, m)

    assert dict(d) == data
