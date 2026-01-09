"""OpenTelemetry integration for pydynox.

This module provides OpenTelemetry tracing for DynamoDB operations.
Requires the opentelemetry-api package.

Example:
    >>> from pydynox.integrations.opentelemetry import enable_otel_tracing
    >>> enable_otel_tracing()
    >>>
    >>> # All operations now create spans automatically
    >>> user = User.get(pk="USER#123")  # Span: "GetItem users"
    >>> user.save()                      # Span: "PutItem users"
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydynox._internal._tracing import (
    disable_tracing,
    enable_tracing,
    is_tracing_enabled,
)

if TYPE_CHECKING:
    from opentelemetry.trace import Tracer

__all__ = [
    "enable_otel_tracing",
    "disable_otel_tracing",
    "is_otel_tracing_enabled",
]


def enable_otel_tracing(
    tracer: Tracer | None = None,
    record_exceptions: bool = True,
    record_consumed_capacity: bool = True,
    span_name_prefix: str | None = None,
) -> None:
    """Enable OpenTelemetry tracing for all pydynox operations.

    Args:
        tracer: Custom tracer. If None, uses global tracer.
        record_exceptions: Add exception events to spans.
        record_consumed_capacity: Add RCU/WCU as span attributes.
        span_name_prefix: Optional prefix for span names.

    Raises:
        ImportError: If opentelemetry-api is not installed.

    Example:
        >>> from pydynox.integrations.opentelemetry import enable_otel_tracing
        >>> enable_otel_tracing()
        >>>
        >>> # Or with custom tracer
        >>> from opentelemetry import trace
        >>> tracer = trace.get_tracer("my-service", "1.0.0")
        >>> enable_otel_tracing(tracer=tracer)
        >>>
        >>> # With custom prefix
        >>> enable_otel_tracing(span_name_prefix="myapp")
        >>> # Spans become: "myapp PutItem users"
    """
    try:
        from opentelemetry import trace as otel_trace
    except ImportError:
        raise ImportError(
            "OpenTelemetry integration requires opentelemetry-api. "
            "Install with: pip install pydynox[opentelemetry]"
        )

    if tracer is None:
        tracer = otel_trace.get_tracer("pydynox")

    enable_tracing(
        tracer=tracer,
        record_exceptions=record_exceptions,
        record_consumed_capacity=record_consumed_capacity,
        span_name_prefix=span_name_prefix,
    )


def disable_otel_tracing() -> None:
    """Disable OpenTelemetry tracing."""
    disable_tracing()


def is_otel_tracing_enabled() -> bool:
    """Check if OpenTelemetry tracing is enabled."""
    return is_tracing_enabled()
