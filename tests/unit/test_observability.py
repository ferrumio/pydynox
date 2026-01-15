"""Unit tests for logging functionality."""

from __future__ import annotations

import logging

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from pydynox import disable_tracing, enable_tracing, set_correlation_id, set_logger
from pydynox._internal._logging import (
    _log_operation,
    get_correlation_id,
    get_logger,
)


def test_default_logger_is_pydynox():
    """Default logger is named 'pydynox'."""
    # WHEN we get the default logger
    logger = get_logger()

    # THEN it should be named 'pydynox'
    assert logger.name == "pydynox"


def test_set_logger_changes_logger():
    """set_logger changes the active logger."""
    # GIVEN the original logger
    original = get_logger()
    custom = logging.getLogger("custom")

    # WHEN we set a custom logger
    set_logger(custom)

    # THEN get_logger should return the custom logger
    assert get_logger() is custom

    # Restore
    set_logger(original)


def test_set_correlation_id():
    """set_correlation_id sets and gets correlation ID."""
    # GIVEN no correlation ID set
    assert get_correlation_id() is None

    # WHEN we set a correlation ID
    set_correlation_id("req-123")

    # THEN it should be retrievable
    assert get_correlation_id() == "req-123"

    # AND can be cleared
    set_correlation_id(None)
    assert get_correlation_id() is None


def test_log_operation_formats_message(caplog):
    """_log_operation formats message correctly."""
    # WHEN we log an operation
    with caplog.at_level(logging.INFO, logger="pydynox"):
        _log_operation("get_item", "users", 12.5, consumed_rcu=0.5)

    # THEN the message should contain operation details
    assert len(caplog.records) == 1
    msg = caplog.records[0].message
    assert "get_item" in msg
    assert "table=users" in msg
    assert "duration_ms=12.5" in msg
    assert "rcu=0.5" in msg


def test_log_operation_with_items_count(caplog):
    """_log_operation includes items count for queries."""
    # WHEN we log a query with items count
    with caplog.at_level(logging.INFO, logger="pydynox"):
        _log_operation("query", "users", 45.0, consumed_rcu=2.5, items_count=10)

    # THEN items count should be in the message
    msg = caplog.records[0].message
    assert "items=10" in msg


def test_log_operation_with_wcu(caplog):
    """_log_operation includes WCU for writes."""
    # WHEN we log a write operation
    with caplog.at_level(logging.INFO, logger="pydynox"):
        _log_operation("put_item", "users", 8.0, consumed_wcu=1.0)

    # THEN WCU should be in the message
    msg = caplog.records[0].message
    assert "wcu=1.0" in msg


class MockLogger:
    """Mock logger for testing custom logger support."""

    def __init__(self):
        self.messages: list[tuple[str, str, dict]] = []

    def info(self, msg: str, **kwargs):
        self.messages.append(("info", msg, kwargs))

    def debug(self, msg: str, **kwargs):
        self.messages.append(("debug", msg, kwargs))

    def warning(self, msg: str, **kwargs):
        self.messages.append(("warning", msg, kwargs))

    def error(self, msg: str, **kwargs):
        self.messages.append(("error", msg, kwargs))


def test_custom_logger_receives_logs():
    """Custom logger receives log messages."""
    # GIVEN a custom mock logger
    original = get_logger()
    mock = MockLogger()

    set_logger(mock)

    # WHEN we log an operation
    _log_operation("get_item", "users", 10.0)

    # THEN the mock logger should receive the message
    assert len(mock.messages) == 1
    level, msg, _ = mock.messages[0]
    assert level == "info"
    assert "get_item" in msg

    # Restore
    set_logger(original)


def test_correlation_id_in_logs():
    """Correlation ID is included in logs when set."""
    # GIVEN a mock logger and correlation ID
    original = get_logger()
    mock = MockLogger()

    set_logger(mock)
    set_correlation_id("req-456")

    # WHEN we log an operation
    _log_operation("get_item", "users", 10.0)

    # THEN correlation ID should be in extra
    _, _, kwargs = mock.messages[0]
    extra = kwargs.get("extra", kwargs)
    assert extra.get("correlation_id") == "req-456"

    # Cleanup
    set_correlation_id(None)
    set_logger(original)


def test_set_logger_with_sdk_debug():
    """set_logger with sdk_debug=True enables SDK debug logs."""
    # GIVEN a mock logger
    original = get_logger()
    mock = MockLogger()

    # WHEN we set logger with sdk_debug=True
    # THEN it should not raise
    set_logger(mock, sdk_debug=True)

    # Restore
    set_logger(original)


def test_trace_context_not_included_when_tracing_disabled():
    """trace_id/span_id not included when tracing is disabled."""
    # GIVEN tracing is disabled
    disable_tracing()

    original = get_logger()
    mock = MockLogger()

    set_logger(mock)

    # WHEN we log an operation
    _log_operation("get_item", "users", 10.0)

    # THEN trace context should not be included
    _, _, kwargs = mock.messages[0]
    extra = kwargs.get("extra", kwargs)
    assert "trace_id" not in extra
    assert "span_id" not in extra

    set_logger(original)


def test_trace_context_included_when_tracing_enabled():
    """trace_id/span_id included in logs when tracing is enabled."""
    # GIVEN OTEL is set up and tracing is enabled
    provider = TracerProvider()
    trace.set_tracer_provider(provider)
    tracer = trace.get_tracer("test")

    original = get_logger()
    mock = MockLogger()

    set_logger(mock)
    enable_tracing()

    # WHEN we log inside a span
    with tracer.start_as_current_span("test_span"):
        _log_operation("get_item", "users", 10.0)

    # THEN trace context should be included
    _, _, kwargs = mock.messages[0]
    extra = kwargs.get("extra", kwargs)
    assert "trace_id" in extra
    assert "span_id" in extra
    assert len(extra["trace_id"]) == 32  # 128-bit hex
    assert len(extra["span_id"]) == 16  # 64-bit hex

    # Cleanup
    disable_tracing()
    set_logger(original)
