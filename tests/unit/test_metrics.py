"""Unit tests for metrics API."""

from __future__ import annotations

import pytest
from pydynox import pydynox_core
from pydynox._internal._metrics import (
    MetricsStorage,
    ModelMetrics,
    OperationMetrics,
)

# ========== OperationMetrics tests ==========


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


# ========== ModelMetrics tests ==========


def test_model_metrics_default():
    """ModelMetrics starts with zero values."""
    m = ModelMetrics()
    assert m.total_rcu == 0.0
    assert m.total_wcu == 0.0
    assert m.total_duration_ms == 0.0
    assert m.operation_count == 0
    assert m.get_count == 0
    assert m.put_count == 0
    assert m.delete_count == 0
    assert m.update_count == 0
    assert m.query_count == 0
    assert m.scan_count == 0


def test_model_metrics_add_get():
    """ModelMetrics.add() tracks get operations."""
    m = ModelMetrics()
    op = pydynox_core.OperationMetrics(duration_ms=10.0)
    # Note: consumed_rcu is set by Rust, we can only test duration_ms here

    m.add(op, "get")

    assert m.total_duration_ms == 10.0
    assert m.operation_count == 1
    assert m.get_count == 1


def test_model_metrics_add_put():
    """ModelMetrics.add() tracks put operations."""
    m = ModelMetrics()
    op = pydynox_core.OperationMetrics(duration_ms=15.0)
    # Note: consumed_wcu is set by Rust, we can only test duration_ms here

    m.add(op, "put")

    assert m.total_duration_ms == 15.0
    assert m.operation_count == 1
    assert m.put_count == 1


def test_model_metrics_add_multiple():
    """ModelMetrics accumulates across multiple operations."""
    m = ModelMetrics()

    op1 = pydynox_core.OperationMetrics(duration_ms=10.0)
    m.add(op1, "get")

    op2 = pydynox_core.OperationMetrics(duration_ms=20.0)
    m.add(op2, "put")

    op3 = pydynox_core.OperationMetrics(duration_ms=5.0)
    m.add(op3, "delete")

    assert m.total_duration_ms == 35.0
    assert m.operation_count == 3
    assert m.get_count == 1
    assert m.put_count == 1
    assert m.delete_count == 1


def test_model_metrics_reset():
    """ModelMetrics.reset() clears all values."""
    m = ModelMetrics()
    op = pydynox_core.OperationMetrics(duration_ms=10.0)
    m.add(op, "get")

    m.reset()

    assert m.total_rcu == 0.0
    assert m.total_wcu == 0.0
    assert m.total_duration_ms == 0.0
    assert m.operation_count == 0
    assert m.get_count == 0


@pytest.mark.parametrize(
    "operation,expected_attr",
    [
        pytest.param("get", "get_count", id="get"),
        pytest.param("put", "put_count", id="put"),
        pytest.param("delete", "delete_count", id="delete"),
        pytest.param("update", "update_count", id="update"),
        pytest.param("query", "query_count", id="query"),
        pytest.param("scan", "scan_count", id="scan"),
    ],
)
def test_model_metrics_operation_counts(operation, expected_attr):
    """ModelMetrics tracks each operation type separately."""
    m = ModelMetrics()
    op = pydynox_core.OperationMetrics(duration_ms=1.0)

    m.add(op, operation)

    assert getattr(m, expected_attr) == 1
    assert m.operation_count == 1


# ========== MetricsStorage tests ==========


def test_metrics_storage_default():
    """MetricsStorage starts empty."""
    s = MetricsStorage()
    assert s.last is None
    assert s.total.operation_count == 0


def test_metrics_storage_record():
    """MetricsStorage.record() stores last and updates total."""
    s = MetricsStorage()
    op = pydynox_core.OperationMetrics(duration_ms=10.0)

    s.record(op, "get")

    assert s.last is op
    assert s.total.total_duration_ms == 10.0
    assert s.total.get_count == 1


def test_metrics_storage_record_multiple():
    """MetricsStorage keeps only the last operation."""
    s = MetricsStorage()

    op1 = pydynox_core.OperationMetrics(duration_ms=10.0)
    s.record(op1, "get")

    op2 = pydynox_core.OperationMetrics(duration_ms=20.0)
    s.record(op2, "put")

    assert s.last is op2
    assert s.total.operation_count == 2


def test_metrics_storage_reset():
    """MetricsStorage.reset() clears last and total."""
    s = MetricsStorage()
    op = pydynox_core.OperationMetrics(duration_ms=10.0)
    s.record(op, "get")

    s.reset()

    assert s.last is None
    assert s.total.operation_count == 0


# ========== Model metrics API tests ==========


def test_model_has_metrics_storage():
    """Each Model class has its own _metrics_storage."""
    from pydynox import Model, ModelConfig
    from pydynox.attributes import StringAttribute

    class TestModel(Model):
        model_config = ModelConfig(table="test")
        pk = StringAttribute(hash_key=True)

    assert hasattr(TestModel, "_metrics_storage")
    assert TestModel._metrics_storage is not None


def test_model_get_last_metrics_none_initially():
    """get_last_metrics() returns None before any operations."""
    from pydynox import Model, ModelConfig
    from pydynox.attributes import StringAttribute

    class TestModel(Model):
        model_config = ModelConfig(table="test")
        pk = StringAttribute(hash_key=True)

    assert TestModel.get_last_metrics() is None


def test_model_get_total_metrics_empty_initially():
    """get_total_metrics() returns empty ModelMetrics before any operations."""
    from pydynox import Model, ModelConfig
    from pydynox.attributes import StringAttribute

    class TestModel(Model):
        model_config = ModelConfig(table="test")
        pk = StringAttribute(hash_key=True)

    metrics = TestModel.get_total_metrics()
    assert metrics.operation_count == 0
    assert metrics.total_rcu == 0.0
    assert metrics.total_wcu == 0.0


def test_model_reset_metrics():
    """reset_metrics() clears all metrics."""
    from pydynox import Model, ModelConfig
    from pydynox.attributes import StringAttribute

    class TestModel(Model):
        model_config = ModelConfig(table="test")
        pk = StringAttribute(hash_key=True)

    # Manually record some metrics
    op = pydynox_core.OperationMetrics(duration_ms=10.0)
    TestModel._record_metrics(op, "get")

    assert TestModel.get_last_metrics() is not None
    assert TestModel.get_total_metrics().operation_count == 1

    TestModel.reset_metrics()

    assert TestModel.get_last_metrics() is None
    assert TestModel.get_total_metrics().operation_count == 0


def test_model_metrics_isolated_per_class():
    """Each Model class has isolated metrics."""
    from pydynox import Model, ModelConfig
    from pydynox.attributes import StringAttribute

    class UserModel(Model):
        model_config = ModelConfig(table="users")
        pk = StringAttribute(hash_key=True)

    class OrderModel(Model):
        model_config = ModelConfig(table="orders")
        pk = StringAttribute(hash_key=True)

    # Record metrics on UserModel
    op = pydynox_core.OperationMetrics(duration_ms=10.0)
    UserModel._record_metrics(op, "get")

    # OrderModel should not be affected
    assert UserModel.get_total_metrics().operation_count == 1
    assert OrderModel.get_total_metrics().operation_count == 0

    # Clean up
    UserModel.reset_metrics()
    OrderModel.reset_metrics()


def test_model_record_metrics():
    """_record_metrics() updates both last and total."""
    from pydynox import Model, ModelConfig
    from pydynox.attributes import StringAttribute

    class TestModel(Model):
        model_config = ModelConfig(table="test")
        pk = StringAttribute(hash_key=True)

    op1 = pydynox_core.OperationMetrics(duration_ms=10.0)
    TestModel._record_metrics(op1, "get")

    assert TestModel.get_last_metrics() is op1
    assert TestModel.get_total_metrics().get_count == 1

    op2 = pydynox_core.OperationMetrics(duration_ms=20.0)
    TestModel._record_metrics(op2, "put")

    assert TestModel.get_last_metrics() is op2
    assert TestModel.get_total_metrics().get_count == 1
    assert TestModel.get_total_metrics().put_count == 1
    assert TestModel.get_total_metrics().operation_count == 2

    # Clean up
    TestModel.reset_metrics()
