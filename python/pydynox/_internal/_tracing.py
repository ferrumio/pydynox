"""Internal tracing helpers for OpenTelemetry integration."""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Generator, Protocol

if TYPE_CHECKING:
    from opentelemetry.trace import Tracer

# Global state
_tracer: Any = None
_config: TracingConfig | None = None

# DynamoDB operation to OTEL operation name mapping
OPERATION_NAMES = {
    "put_item": "PutItem",
    "get_item": "GetItem",
    "delete_item": "DeleteItem",
    "update_item": "UpdateItem",
    "query": "Query",
    "scan": "Scan",
    "batch_write": "BatchWriteItem",
    "batch_get": "BatchGetItem",
    "transact_write": "TransactWriteItems",
    "transact_get": "TransactGetItems",
}


class TracingConfig:
    """Configuration for tracing."""

    def __init__(
        self,
        record_exceptions: bool = True,
        record_consumed_capacity: bool = True,
        span_name_prefix: str | None = None,
    ):
        self.record_exceptions = record_exceptions
        self.record_consumed_capacity = record_consumed_capacity
        self.span_name_prefix = span_name_prefix


class SpanProtocol(Protocol):
    """Protocol for span objects."""

    def set_attribute(self, key: str, value: Any) -> None: ...
    def record_exception(self, exception: BaseException) -> None: ...
    def set_status(self, status: Any, description: str | None = None) -> None: ...
    def end(self) -> None: ...


class TracerProtocol(Protocol):
    """Protocol for tracer objects."""

    def start_span(self, name: str, **kwargs: Any) -> SpanProtocol: ...


def enable_tracing(
    tracer: TracerProtocol | Tracer | None = None,
    record_exceptions: bool = True,
    record_consumed_capacity: bool = True,
    span_name_prefix: str | None = None,
) -> None:
    """Enable tracing for all pydynox operations.

    Args:
        tracer: Custom tracer. If None, uses global OTEL tracer.
        record_exceptions: Add exception events to spans.
        record_consumed_capacity: Add RCU/WCU as span attributes.
        span_name_prefix: Optional prefix for span names.

    Example:
        >>> from pydynox import enable_tracing
        >>> enable_tracing()
        >>>
        >>> # With custom tracer
        >>> from opentelemetry import trace
        >>> tracer = trace.get_tracer("my-service")
        >>> enable_tracing(tracer=tracer)
    """
    global _tracer, _config

    if tracer is None:
        try:
            from opentelemetry import trace

            tracer = trace.get_tracer("pydynox")
        except ImportError:
            raise ImportError(
                "OpenTelemetry tracing requires opentelemetry-api. "
                "Install with: pip install pydynox[opentelemetry]"
            )

    _tracer = tracer
    _config = TracingConfig(
        record_exceptions=record_exceptions,
        record_consumed_capacity=record_consumed_capacity,
        span_name_prefix=span_name_prefix,
    )


def disable_tracing() -> None:
    """Disable tracing."""
    global _tracer, _config
    _tracer = None
    _config = None


def is_tracing_enabled() -> bool:
    """Check if tracing is enabled."""
    return _tracer is not None


def get_tracer() -> Any:
    """Get the current tracer."""
    return _tracer


def get_config() -> TracingConfig | None:
    """Get the current tracing config."""
    return _config


def get_operation_name(operation: str) -> str:
    """Get OTEL operation name from internal operation name.

    Handles both sync and async variants (put_item, async_put_item -> PutItem).
    """
    base_op = operation.removeprefix("async_")
    return OPERATION_NAMES.get(base_op, operation)


def _build_span_name(
    otel_operation: str,
    table: str | None,
    batch_size: int | None,
    prefix: str | None,
) -> str:
    """Build span name following OTEL conventions."""
    if batch_size and batch_size > 1:
        span_name = f"BATCH {otel_operation}"
        if table:
            span_name = f"BATCH {otel_operation} {table}"
    else:
        span_name = otel_operation
        if table:
            span_name = f"{otel_operation} {table}"

    if prefix:
        span_name = f"{prefix} {span_name}"

    return span_name


def _set_span_attributes(
    span: SpanProtocol,
    otel_operation: str,
    table: str | None,
    region: str | None,
    batch_size: int | None,
) -> None:
    """Set standard attributes on a span."""
    span.set_attribute("db.system.name", "aws.dynamodb")
    span.set_attribute("db.operation.name", otel_operation)

    if table:
        span.set_attribute("db.collection.name", table)
    if region:
        span.set_attribute("db.namespace", region)
        span.set_attribute("server.address", f"dynamodb.{region}.amazonaws.com")
    if batch_size and batch_size > 1:
        span.set_attribute("db.operation.batch.size", batch_size)


@contextmanager
def trace_operation(
    operation: str,
    table: str | None = None,
    region: str | None = None,
    batch_size: int | None = None,
) -> Generator[SpanProtocol | None, None, None]:
    """Context manager to trace a DynamoDB operation.

    Internal function called by client operations.
    Follows OTEL Database Semantic Conventions.

    The span is created as a child of the current active span (if any),
    enabling distributed tracing across your application.

    Args:
        operation: Internal operation name (e.g., "put_item", "async_get_item").
        table: DynamoDB table name.
        region: AWS region.
        batch_size: Number of items in batch operation.

    Yields:
        Span object if tracing is enabled, None otherwise.
    """
    if not is_tracing_enabled():
        yield None
        return

    tracer = get_tracer()
    config = get_config()

    if tracer is None or config is None:
        yield None
        return

    try:
        from opentelemetry.trace import SpanKind, StatusCode
    except ImportError:
        yield None
        return

    otel_operation = get_operation_name(operation)
    span_name = _build_span_name(otel_operation, table, batch_size, config.span_name_prefix)

    # Use start_as_current_span to automatically:
    # 1. Set this span as child of current active span (context propagation)
    # 2. Make this span the current span for nested operations
    # 3. End the span when context exits
    with tracer.start_as_current_span(
        span_name,
        kind=SpanKind.CLIENT,
        end_on_exit=False,  # We handle end() manually for error handling
    ) as span:
        _set_span_attributes(span, otel_operation, table, region, batch_size)

        try:
            yield span
        except Exception as e:
            span.set_attribute("error.type", type(e).__name__)
            if config.record_exceptions:
                span.record_exception(e)
            span.set_status(StatusCode.ERROR, str(e))
            raise
        finally:
            span.end()


def add_response_attributes(
    span: SpanProtocol | None,
    consumed_rcu: float | None = None,
    consumed_wcu: float | None = None,
    request_id: str | None = None,
) -> None:
    """Add response attributes to a span.

    Args:
        span: The span to add attributes to.
        consumed_rcu: Read capacity units consumed.
        consumed_wcu: Write capacity units consumed.
        request_id: AWS request ID.
    """
    if span is None:
        return

    config = get_config()
    if config is None or not config.record_consumed_capacity:
        return

    if consumed_rcu is not None:
        span.set_attribute("aws.dynamodb.consumed_capacity.read", consumed_rcu)
    if consumed_wcu is not None:
        span.set_attribute("aws.dynamodb.consumed_capacity.write", consumed_wcu)
    if request_id is not None:
        span.set_attribute("aws.request_id", request_id)
