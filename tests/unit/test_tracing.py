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
    # THEN tracing is disabled and returns None
    assert is_tracing_enabled() is False
    assert get_tracer() is None
    assert get_config() is None


def test_enable_tracing_with_mock_tracer():
    """Enable tracing with a mock tracer."""
    # GIVEN a mock tracer
    mock_tracer = MagicMock()

    # WHEN enabling tracing
    enable_tracing(tracer=mock_tracer)

    # THEN tracing is enabled with the tracer
    assert is_tracing_enabled() is True
    assert get_tracer() is mock_tracer
    assert get_config() is not None


def test_disable_tracing():
    """Disable tracing after enabling."""
    # GIVEN tracing is enabled
    mock_tracer = MagicMock()
    enable_tracing(tracer=mock_tracer)

    # WHEN disabling tracing
    disable_tracing()

    # THEN tracing is disabled
    assert is_tracing_enabled() is False
    assert get_tracer() is None
    assert get_config() is None


def test_tracing_config_defaults():
    """TracingConfig should have correct defaults."""
    # WHEN creating a config with defaults
    config = TracingConfig()

    # THEN defaults are set correctly
    assert config.record_exceptions is True
    assert config.record_consumed_capacity is True
    assert config.span_name_prefix is None


def test_tracing_config_custom():
    """TracingConfig should accept custom values."""
    # WHEN creating a config with custom values
    config = TracingConfig(
        record_exceptions=False,
        record_consumed_capacity=False,
        span_name_prefix="myapp",
    )

    # THEN custom values are stored
    assert config.record_exceptions is False
    assert config.record_consumed_capacity is False
    assert config.span_name_prefix == "myapp"


def test_enable_tracing_with_config():
    """Enable tracing with custom config."""
    # GIVEN a mock tracer
    mock_tracer = MagicMock()

    # WHEN enabling tracing with custom config
    enable_tracing(
        tracer=mock_tracer,
        record_exceptions=False,
        record_consumed_capacity=False,
        span_name_prefix="myapp",
    )

    # THEN config is stored with custom values
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
    # WHEN using trace_operation with tracing disabled
    with trace_operation("put_item", "users", "us-east-1") as span:
        # THEN span is None
        assert span is None


def test_trace_operation_enabled():
    """trace_operation should create span when tracing is enabled."""
    # GIVEN tracing is enabled with a mock tracer
    mock_span = MagicMock()
    mock_tracer = MagicMock()
    mock_tracer.start_as_current_span.return_value.__enter__ = MagicMock(return_value=mock_span)
    mock_tracer.start_as_current_span.return_value.__exit__ = MagicMock(return_value=False)
    enable_tracing(tracer=mock_tracer)

    # WHEN using trace_operation
    with patch.dict("sys.modules", {"opentelemetry.trace": MagicMock()}):
        with trace_operation("put_item", "users", "us-east-1") as span:
            # THEN span is returned
            assert span is mock_span

    # THEN span was created with correct name and ended
    mock_tracer.start_as_current_span.assert_called_once()
    call_args = mock_tracer.start_as_current_span.call_args
    assert call_args[0][0] == "PutItem users"
    mock_span.end.assert_called_once()


def test_trace_operation_sets_attributes():
    """trace_operation should set correct attributes."""
    # GIVEN tracing is enabled
    mock_span = MagicMock()
    mock_tracer = MagicMock()
    mock_tracer.start_as_current_span.return_value.__enter__ = MagicMock(return_value=mock_span)
    mock_tracer.start_as_current_span.return_value.__exit__ = MagicMock(return_value=False)
    enable_tracing(tracer=mock_tracer)

    # WHEN using trace_operation
    with patch.dict("sys.modules", {"opentelemetry.trace": MagicMock()}):
        with trace_operation("put_item", "users", "us-east-1"):
            pass

    # THEN correct attributes are set on the span
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
    # GIVEN tracing is enabled with a prefix
    mock_span = MagicMock()
    mock_tracer = MagicMock()
    mock_tracer.start_as_current_span.return_value.__enter__ = MagicMock(return_value=mock_span)
    mock_tracer.start_as_current_span.return_value.__exit__ = MagicMock(return_value=False)
    enable_tracing(tracer=mock_tracer, span_name_prefix="myapp")

    # WHEN using trace_operation
    with patch.dict("sys.modules", {"opentelemetry.trace": MagicMock()}):
        with trace_operation("put_item", "users"):
            pass

    # THEN span name includes the prefix
    call_args = mock_tracer.start_as_current_span.call_args
    assert call_args[0][0] == "myapp PutItem users"


def test_trace_operation_batch():
    """trace_operation should handle batch operations."""
    # GIVEN tracing is enabled
    mock_span = MagicMock()
    mock_tracer = MagicMock()
    mock_tracer.start_as_current_span.return_value.__enter__ = MagicMock(return_value=mock_span)
    mock_tracer.start_as_current_span.return_value.__exit__ = MagicMock(return_value=False)
    enable_tracing(tracer=mock_tracer)

    # WHEN using trace_operation for a batch operation
    with patch.dict("sys.modules", {"opentelemetry.trace": MagicMock()}):
        with trace_operation("batch_write", "users", batch_size=25):
            pass

    # THEN span name includes BATCH prefix and batch size is set
    call_args = mock_tracer.start_as_current_span.call_args
    assert call_args[0][0] == "BATCH BatchWriteItem users"
    set_attribute_calls = {
        call[0][0]: call[0][1] for call in mock_span.set_attribute.call_args_list
    }
    assert set_attribute_calls["db.operation.batch.size"] == 25


def test_trace_operation_no_table():
    """trace_operation should work without table name."""
    # GIVEN tracing is enabled
    mock_span = MagicMock()
    mock_tracer = MagicMock()
    mock_tracer.start_as_current_span.return_value.__enter__ = MagicMock(return_value=mock_span)
    mock_tracer.start_as_current_span.return_value.__exit__ = MagicMock(return_value=False)
    enable_tracing(tracer=mock_tracer)

    # WHEN using trace_operation without table name
    with patch.dict("sys.modules", {"opentelemetry.trace": MagicMock()}):
        with trace_operation("query"):
            pass

    # THEN span name is just the operation
    call_args = mock_tracer.start_as_current_span.call_args
    assert call_args[0][0] == "Query"


def test_trace_operation_exception():
    """trace_operation should record exceptions."""
    # GIVEN tracing is enabled
    mock_span = MagicMock()
    mock_tracer = MagicMock()
    mock_tracer.start_as_current_span.return_value.__enter__ = MagicMock(return_value=mock_span)
    mock_tracer.start_as_current_span.return_value.__exit__ = MagicMock(return_value=False)
    enable_tracing(tracer=mock_tracer)
    mock_otel = MagicMock()
    mock_otel.StatusCode.ERROR = "ERROR"

    # WHEN an exception is raised inside trace_operation
    with patch.dict("sys.modules", {"opentelemetry.trace": mock_otel}):
        with pytest.raises(ValueError):
            with trace_operation("put_item", "users"):
                raise ValueError("test error")

    # THEN error is recorded on the span
    mock_span.set_attribute.assert_any_call("error.type", "ValueError")
    mock_span.record_exception.assert_called_once()
    mock_span.set_status.assert_called_once()
    mock_span.end.assert_called_once()


def test_trace_operation_exception_not_recorded():
    """trace_operation should not record exceptions when disabled."""
    # GIVEN tracing is enabled with record_exceptions=False
    mock_span = MagicMock()
    mock_tracer = MagicMock()
    mock_tracer.start_as_current_span.return_value.__enter__ = MagicMock(return_value=mock_span)
    mock_tracer.start_as_current_span.return_value.__exit__ = MagicMock(return_value=False)
    enable_tracing(tracer=mock_tracer, record_exceptions=False)
    mock_otel = MagicMock()
    mock_otel.StatusCode.ERROR = "ERROR"

    # WHEN an exception is raised
    with patch.dict("sys.modules", {"opentelemetry.trace": mock_otel}):
        with pytest.raises(ValueError):
            with trace_operation("put_item", "users"):
                raise ValueError("test error")

    # THEN exception is NOT recorded but error.type is still set
    mock_span.record_exception.assert_not_called()
    mock_span.set_attribute.assert_any_call("error.type", "ValueError")


def test_add_response_attributes():
    """add_response_attributes should add metrics to span."""
    # GIVEN tracing is enabled
    mock_span = MagicMock()
    mock_tracer = MagicMock()
    enable_tracing(tracer=mock_tracer)

    # WHEN adding response attributes
    add_response_attributes(
        mock_span,
        consumed_rcu=1.5,
        consumed_wcu=2.0,
        request_id="ABC123",
    )

    # THEN attributes are set on the span
    mock_span.set_attribute.assert_any_call("aws.dynamodb.consumed_capacity.read", 1.5)
    mock_span.set_attribute.assert_any_call("aws.dynamodb.consumed_capacity.write", 2.0)
    mock_span.set_attribute.assert_any_call("aws.request_id", "ABC123")


def test_add_response_attributes_disabled():
    """add_response_attributes should do nothing when capacity recording is disabled."""
    # GIVEN tracing is enabled with record_consumed_capacity=False
    mock_span = MagicMock()
    mock_tracer = MagicMock()
    enable_tracing(tracer=mock_tracer, record_consumed_capacity=False)

    # WHEN adding response attributes
    add_response_attributes(
        mock_span,
        consumed_rcu=1.5,
        consumed_wcu=2.0,
        request_id="ABC123",
    )

    # THEN no attributes are set
    mock_span.set_attribute.assert_not_called()


def test_add_response_attributes_none_span():
    """add_response_attributes should handle None span."""
    # WHEN calling with None span
    # THEN it should not raise
    add_response_attributes(None, consumed_rcu=1.5)


def test_operation_names_complete():
    """All expected operations should be in OPERATION_NAMES."""
    # GIVEN a list of expected operations
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

    # THEN all operations are in OPERATION_NAMES
    for op in expected_ops:
        assert op in OPERATION_NAMES, f"Missing operation: {op}"
