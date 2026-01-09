"""Unit tests for OpenTelemetry tracing integration."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from pydynox._internal._tracing import (
    OPERATION_NAMES,
    TracingConfig,
    add_response_attributes,
    disable_tracing,
    enable_tracing,
    get_config,
    get_operation_name,
    get_tracer,
    is_tracing_enabled,
    trace_operation,
)


@pytest.fixture(autouse=True)
def reset_tracing():
    """Reset tracing state before and after each test."""
    disable_tracing()
    yield
    disable_tracing()


def test_tracing_disabled_by_default():
    """Tracing should be disabled by default."""
    assert is_tracing_enabled() is False
    assert get_tracer() is None
    assert get_config() is None


def test_enable_tracing_with_mock_tracer():
    """Enable tracing with a mock tracer."""
    mock_tracer = MagicMock()

    enable_tracing(tracer=mock_tracer)

    assert is_tracing_enabled() is True
    assert get_tracer() is mock_tracer
    assert get_config() is not None


def test_disable_tracing():
    """Disable tracing after enabling."""
    mock_tracer = MagicMock()
    enable_tracing(tracer=mock_tracer)

    disable_tracing()

    assert is_tracing_enabled() is False
    assert get_tracer() is None
    assert get_config() is None


def test_tracing_config_defaults():
    """TracingConfig should have correct defaults."""
    config = TracingConfig()

    assert config.record_exceptions is True
    assert config.record_consumed_capacity is True
    assert config.span_name_prefix is None


def test_tracing_config_custom():
    """TracingConfig should accept custom values."""
    config = TracingConfig(
        record_exceptions=False,
        record_consumed_capacity=False,
        span_name_prefix="myapp",
    )

    assert config.record_exceptions is False
    assert config.record_consumed_capacity is False
    assert config.span_name_prefix == "myapp"


def test_enable_tracing_with_config():
    """Enable tracing with custom config."""
    mock_tracer = MagicMock()

    enable_tracing(
        tracer=mock_tracer,
        record_exceptions=False,
        record_consumed_capacity=False,
        span_name_prefix="myapp",
    )

    config = get_config()
    assert config is not None
    assert config.record_exceptions is False
    assert config.record_consumed_capacity is False
    assert config.span_name_prefix == "myapp"


@pytest.mark.parametrize(
    "operation,expected",
    [
        pytest.param("put_item", "PutItem", id="put_item"),
        pytest.param("get_item", "GetItem", id="get_item"),
        pytest.param("delete_item", "DeleteItem", id="delete_item"),
        pytest.param("update_item", "UpdateItem", id="update_item"),
        pytest.param("query", "Query", id="query"),
        pytest.param("scan", "Scan", id="scan"),
        pytest.param("batch_write", "BatchWriteItem", id="batch_write"),
        pytest.param("batch_get", "BatchGetItem", id="batch_get"),
        pytest.param("transact_write", "TransactWriteItems", id="transact_write"),
        pytest.param("transact_get", "TransactGetItems", id="transact_get"),
    ],
)
def test_get_operation_name(operation: str, expected: str):
    """get_operation_name should return correct OTEL operation name."""
    assert get_operation_name(operation) == expected


@pytest.mark.parametrize(
    "operation,expected",
    [
        pytest.param("async_put_item", "PutItem", id="async_put_item"),
        pytest.param("async_get_item", "GetItem", id="async_get_item"),
        pytest.param("async_delete_item", "DeleteItem", id="async_delete_item"),
        pytest.param("async_update_item", "UpdateItem", id="async_update_item"),
    ],
)
def test_get_operation_name_async(operation: str, expected: str):
    """get_operation_name should handle async_ prefix."""
    assert get_operation_name(operation) == expected


def test_get_operation_name_unknown():
    """get_operation_name should return original name for unknown operations."""
    assert get_operation_name("unknown_op") == "unknown_op"


def test_trace_operation_disabled():
    """trace_operation should yield None when tracing is disabled."""
    with trace_operation("put_item", "users", "us-east-1") as span:
        assert span is None


def test_trace_operation_enabled():
    """trace_operation should create span when tracing is enabled."""
    mock_span = MagicMock()
    mock_tracer = MagicMock()
    # start_as_current_span is a context manager that returns the span
    mock_tracer.start_as_current_span.return_value.__enter__ = MagicMock(return_value=mock_span)
    mock_tracer.start_as_current_span.return_value.__exit__ = MagicMock(return_value=False)

    enable_tracing(tracer=mock_tracer)

    with patch.dict("sys.modules", {"opentelemetry.trace": MagicMock()}):
        with trace_operation("put_item", "users", "us-east-1") as span:
            assert span is mock_span

    # Verify span was created with correct name
    mock_tracer.start_as_current_span.assert_called_once()
    call_args = mock_tracer.start_as_current_span.call_args
    assert call_args[0][0] == "PutItem users"

    # Verify span was ended
    mock_span.end.assert_called_once()


def test_trace_operation_sets_attributes():
    """trace_operation should set correct attributes."""
    mock_span = MagicMock()
    mock_tracer = MagicMock()
    mock_tracer.start_as_current_span.return_value.__enter__ = MagicMock(return_value=mock_span)
    mock_tracer.start_as_current_span.return_value.__exit__ = MagicMock(return_value=False)

    enable_tracing(tracer=mock_tracer)

    with patch.dict("sys.modules", {"opentelemetry.trace": MagicMock()}):
        with trace_operation("put_item", "users", "us-east-1"):
            pass

    # Check attributes were set
    set_attribute_calls = {
        call[0][0]: call[0][1] for call in mock_span.set_attribute.call_args_list
    }
    assert set_attribute_calls["db.system.name"] == "aws.dynamodb"
    assert set_attribute_calls["db.operation.name"] == "PutItem"
    assert set_attribute_calls["db.collection.name"] == "users"
    assert set_attribute_calls["db.namespace"] == "us-east-1"
    assert set_attribute_calls["server.address"] == "dynamodb.us-east-1.amazonaws.com"


def test_trace_operation_with_prefix():
    """trace_operation should add prefix to span name."""
    mock_span = MagicMock()
    mock_tracer = MagicMock()
    mock_tracer.start_as_current_span.return_value.__enter__ = MagicMock(return_value=mock_span)
    mock_tracer.start_as_current_span.return_value.__exit__ = MagicMock(return_value=False)

    enable_tracing(tracer=mock_tracer, span_name_prefix="myapp")

    with patch.dict("sys.modules", {"opentelemetry.trace": MagicMock()}):
        with trace_operation("put_item", "users"):
            pass

    call_args = mock_tracer.start_as_current_span.call_args
    assert call_args[0][0] == "myapp PutItem users"


def test_trace_operation_batch():
    """trace_operation should handle batch operations."""
    mock_span = MagicMock()
    mock_tracer = MagicMock()
    mock_tracer.start_as_current_span.return_value.__enter__ = MagicMock(return_value=mock_span)
    mock_tracer.start_as_current_span.return_value.__exit__ = MagicMock(return_value=False)

    enable_tracing(tracer=mock_tracer)

    with patch.dict("sys.modules", {"opentelemetry.trace": MagicMock()}):
        with trace_operation("batch_write", "users", batch_size=25):
            pass

    call_args = mock_tracer.start_as_current_span.call_args
    assert call_args[0][0] == "BATCH BatchWriteItem users"

    set_attribute_calls = {
        call[0][0]: call[0][1] for call in mock_span.set_attribute.call_args_list
    }
    assert set_attribute_calls["db.operation.batch.size"] == 25


def test_trace_operation_no_table():
    """trace_operation should work without table name."""
    mock_span = MagicMock()
    mock_tracer = MagicMock()
    mock_tracer.start_as_current_span.return_value.__enter__ = MagicMock(return_value=mock_span)
    mock_tracer.start_as_current_span.return_value.__exit__ = MagicMock(return_value=False)

    enable_tracing(tracer=mock_tracer)

    with patch.dict("sys.modules", {"opentelemetry.trace": MagicMock()}):
        with trace_operation("query"):
            pass

    call_args = mock_tracer.start_as_current_span.call_args
    assert call_args[0][0] == "Query"


def test_trace_operation_exception():
    """trace_operation should record exceptions."""
    mock_span = MagicMock()
    mock_tracer = MagicMock()
    mock_tracer.start_as_current_span.return_value.__enter__ = MagicMock(return_value=mock_span)
    mock_tracer.start_as_current_span.return_value.__exit__ = MagicMock(return_value=False)

    enable_tracing(tracer=mock_tracer)

    mock_otel = MagicMock()
    mock_otel.StatusCode.ERROR = "ERROR"

    with patch.dict("sys.modules", {"opentelemetry.trace": mock_otel}):
        with pytest.raises(ValueError):
            with trace_operation("put_item", "users"):
                raise ValueError("test error")

    # Verify error was recorded
    mock_span.set_attribute.assert_any_call("error.type", "ValueError")
    mock_span.record_exception.assert_called_once()
    mock_span.set_status.assert_called_once()
    mock_span.end.assert_called_once()


def test_trace_operation_exception_not_recorded():
    """trace_operation should not record exceptions when disabled."""
    mock_span = MagicMock()
    mock_tracer = MagicMock()
    mock_tracer.start_as_current_span.return_value.__enter__ = MagicMock(return_value=mock_span)
    mock_tracer.start_as_current_span.return_value.__exit__ = MagicMock(return_value=False)

    enable_tracing(tracer=mock_tracer, record_exceptions=False)

    mock_otel = MagicMock()
    mock_otel.StatusCode.ERROR = "ERROR"

    with patch.dict("sys.modules", {"opentelemetry.trace": mock_otel}):
        with pytest.raises(ValueError):
            with trace_operation("put_item", "users"):
                raise ValueError("test error")

    # Verify exception was NOT recorded
    mock_span.record_exception.assert_not_called()
    # But error.type should still be set
    mock_span.set_attribute.assert_any_call("error.type", "ValueError")


def test_add_response_attributes():
    """add_response_attributes should add metrics to span."""
    mock_span = MagicMock()
    mock_tracer = MagicMock()

    enable_tracing(tracer=mock_tracer)

    add_response_attributes(
        mock_span,
        consumed_rcu=1.5,
        consumed_wcu=2.0,
        request_id="ABC123",
    )

    mock_span.set_attribute.assert_any_call("aws.dynamodb.consumed_capacity.read", 1.5)
    mock_span.set_attribute.assert_any_call("aws.dynamodb.consumed_capacity.write", 2.0)
    mock_span.set_attribute.assert_any_call("aws.request_id", "ABC123")


def test_add_response_attributes_disabled():
    """add_response_attributes should do nothing when capacity recording is disabled."""
    mock_span = MagicMock()
    mock_tracer = MagicMock()

    enable_tracing(tracer=mock_tracer, record_consumed_capacity=False)

    add_response_attributes(
        mock_span,
        consumed_rcu=1.5,
        consumed_wcu=2.0,
        request_id="ABC123",
    )

    mock_span.set_attribute.assert_not_called()


def test_add_response_attributes_none_span():
    """add_response_attributes should handle None span."""
    # Should not raise
    add_response_attributes(None, consumed_rcu=1.5)


def test_operation_names_complete():
    """All expected operations should be in OPERATION_NAMES."""
    expected_ops = [
        "put_item",
        "get_item",
        "delete_item",
        "update_item",
        "query",
        "scan",
        "batch_write",
        "batch_get",
        "transact_write",
        "transact_get",
    ]
    for op in expected_ops:
        assert op in OPERATION_NAMES, f"Missing operation: {op}"
