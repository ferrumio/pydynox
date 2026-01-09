"""Custom tracer and configuration example."""

from opentelemetry import trace
from pydynox import enable_tracing

# Use a custom tracer
tracer = trace.get_tracer("my-service", "1.0.0")

enable_tracing(
    tracer=tracer,
    record_exceptions=True,  # Add exception events to spans
    record_consumed_capacity=True,  # Add RCU/WCU as attributes
    span_name_prefix="myapp",  # Spans become: "myapp PutItem users"
)
