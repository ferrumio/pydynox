# Observability

Know what's happening in your DynamoDB operations. pydynox gives you metrics on every call - duration, capacity consumed, items returned. No extra code needed.

## Why observability matters

DynamoDB bills by capacity consumed. Without metrics, you're flying blind:

- Is that query using 1 RCU or 100?
- Why is this Lambda timing out?
- Which operation is eating all my capacity?

pydynox answers these questions automatically. Every operation returns metrics, and logs are built-in.

## Key features

- Metrics on every operation (duration, RCU/WCU, item counts)
- Model-level metrics with class methods (no field conflicts)
- Automatic logging at INFO level
- Custom logger support (Powertools, structlog)
- Correlation ID for request tracing
- AWS SDK debug logs when you need them

## Getting started

pydynox has two ways to access metrics:

1. **Client metrics** - Direct access on client operations (low-level)
2. **Model metrics** - Class methods on Model classes (high-level)

### Client metrics

For low-level client operations, use `client.get_last_metrics()` and `client.get_total_metrics()`.

Write operations also return metrics directly:

=== "put_item_metrics.py"
    ```python
    --8<-- "docs/examples/observability/put_item_metrics.py"
    ```

Read operations store metrics for retrieval:

=== "get_item_metrics.py"
    ```python
    --8<-- "docs/examples/observability/get_item_metrics.py"
    ```

Get total metrics across all operations:

=== "client_total_metrics.py"
    ```python
    --8<-- "docs/examples/observability/client_total_metrics.py"
    ```

### Model metrics

For Model operations, use class methods. This avoids conflicts with user fields named "metrics".

=== "model_metrics.py"
    ```python
    --8<-- "docs/examples/observability/model_metrics.py"
    ```

Each Model class has isolated metrics:

=== "model_metrics_isolated.py"
    ```python
    --8<-- "docs/examples/observability/model_metrics_isolated.py"
    ```

### Reset metrics per request

In long-running processes (FastAPI, Flask), metrics accumulate forever. Reset at the start of each request:

=== "model_metrics_reset.py"
    ```python
    --8<-- "docs/examples/observability/model_metrics_reset.py"
    ```

=== "client_reset_metrics.py"
    ```python
    --8<-- "docs/examples/observability/client_reset_metrics.py"
    ```

### What's in metrics

| Field | Type | Description |
|-------|------|-------------|
| `duration_ms` | float | How long the operation took |
| `consumed_rcu` | float or None | Read capacity units used |
| `consumed_wcu` | float or None | Write capacity units used |
| `items_count` | int or None | Items returned (query/scan) |
| `scanned_count` | int or None | Items scanned before filtering |
| `request_id` | str or None | AWS request ID for support tickets |

### Model total metrics

`get_total_metrics()` returns aggregated metrics:

| Field | Type | Description |
|-------|------|-------------|
| `total_rcu` | float | Total RCU consumed |
| `total_wcu` | float | Total WCU consumed |
| `total_duration_ms` | float | Total time spent |
| `operation_count` | int | Total operations |
| `get_count` | int | Number of get operations |
| `put_count` | int | Number of put operations |
| `delete_count` | int | Number of delete operations |
| `update_count` | int | Number of update operations |
| `query_count` | int | Number of query operations |
| `scan_count` | int | Number of scan operations |
| `kms_duration_ms` | float | Time spent on KMS calls |
| `kms_calls` | int | Number of KMS API calls |

### Automatic logging

pydynox logs every operation at INFO level. Just configure Python logging:

=== "basic_logging.py"
    ```python
    --8<-- "docs/examples/observability/basic_logging.py"
    ```

Output:

```
INFO:pydynox:put_item table=users duration_ms=8.2 wcu=1.0
INFO:pydynox:get_item table=users duration_ms=12.1 rcu=0.5
INFO:pydynox:query table=users duration_ms=45.2 rcu=2.5 items=10
```

Slow operations (>100ms) get a warning:

```
WARNING:pydynox:query slow operation (150.3ms)
```

### Disable logging

If you don't want pydynox logs at all:

=== "disable_logging.py"
    ```python
    --8<-- "docs/examples/observability/disable_logging.py"
    ```

## Advanced

### Custom logger

Send pydynox logs to your own logger with `set_logger()`:

=== "custom_logger.py"
    ```python
    --8<-- "docs/examples/observability/custom_logger.py"
    ```

Works with any logger that has `debug`, `info`, `warning`, `error` methods. Great for AWS Lambda Powertools or structlog.

### Correlation ID

Track requests across your logs with `set_correlation_id()`:

=== "correlation_id.py"
    ```python
    --8<-- "docs/examples/observability/correlation_id.py"
    ```

All pydynox logs will include the correlation ID. Useful in Lambda where you want to trace a request through multiple DynamoDB calls.

### SDK debug logs

For deep debugging, enable AWS SDK logs:

=== "sdk_debug.py"
    ```python
    --8<-- "docs/examples/observability/sdk_debug.py"
    ```

Or via environment variable:

```bash
# Basic SDK logs
RUST_LOG=aws_sdk_dynamodb=debug python app.py

# Full detail (HTTP bodies, retries, credentials)
RUST_LOG=aws_sdk_dynamodb=trace,aws_smithy_runtime=trace python app.py
```

!!! warning
    SDK debug logs are verbose. Only enable when debugging specific issues.

### Log levels

| Level | What's logged |
|-------|---------------|
| ERROR | Exceptions, failed operations |
| WARNING | Slow queries (>100ms) |
| INFO | Operation summary (table, duration, rcu/wcu) |
| DEBUG | Detailed request/response info |

## Use cases

### Cost monitoring

Track capacity consumption per operation:

```python
result = client.get_item("users", {"pk": "USER#123"})
print(f"This read cost {result.metrics.consumed_rcu} RCU")

# Over time, aggregate these to understand costs
```

### Performance debugging

Find slow operations:

```python
result = client.query(...)
if result.metrics.duration_ms > 100:
    logger.warning(f"Slow query: {result.metrics.duration_ms}ms")
```

### Lambda optimization

In Lambda, every millisecond counts:

```python
def handler(event, context):
    set_correlation_id(context.aws_request_id)
    
    user = User.get(pk=event["user_id"])
    # Logs include request ID for tracing
    
    return {"statusCode": 200}
```


## OpenTelemetry tracing

pydynox supports OpenTelemetry for distributed tracing. When enabled, every DynamoDB operation creates a span with useful attributes.

### Installation

Install the optional dependency:

```bash
pip install pydynox[opentelemetry]
```

### Basic usage

=== "tracing_basic.py"
    ```python
    --8<-- "docs/examples/observability/tracing_basic.py"
    ```

### Span attributes

Each span follows [OTEL Database Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/database/database-spans/):

| Attribute | Example | Description |
|-----------|---------|-------------|
| `db.system.name` | `aws.dynamodb` | Database system |
| `db.operation.name` | `PutItem` | DynamoDB operation |
| `db.collection.name` | `users` | Table name |
| `db.namespace` | `us-east-1` | AWS region |
| `server.address` | `dynamodb.us-east-1.amazonaws.com` | Endpoint |
| `aws.dynamodb.consumed_capacity.read` | `1.0` | RCU consumed |
| `aws.dynamodb.consumed_capacity.write` | `1.0` | WCU consumed |
| `aws.request_id` | `ABC123...` | AWS request ID |
| `error.type` | `ConditionalCheckFailedException` | Error class (if failed) |

### Custom configuration

=== "tracing_custom.py"
    ```python
    --8<-- "docs/examples/observability/tracing_custom.py"
    ```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `tracer` | Tracer | None | Custom OTEL tracer |
| `record_exceptions` | bool | True | Add exception events to spans |
| `record_consumed_capacity` | bool | True | Add RCU/WCU as attributes |
| `span_name_prefix` | str | None | Prefix for span names |

### Disable tracing

=== "tracing_disable.py"
    ```python
    --8<-- "docs/examples/observability/tracing_disable.py"
    ```

### Span naming

Span names follow OTEL conventions:

- Single operation: `"PutItem users"`
- Batch operation: `"BATCH BatchWriteItem users"`
- With prefix: `"myapp PutItem users"`

### Context propagation

pydynox spans automatically connect to the current active span. This means if you create a parent span in your code, all DynamoDB operations inside it become child spans.

```python
from opentelemetry import trace
from pydynox import enable_tracing, Model

enable_tracing()
tracer = trace.get_tracer("my-service")

# In a Lambda handler or HTTP request
with tracer.start_as_current_span("handle_request"):
    user = User.get(pk="USER#123")  # Child span: "GetItem users"
    user.name = "Updated"
    user.save()                      # Child span: "PutItem users"
```

All spans share the same `trace_id`, so you can see the full request flow in your tracing backend (Jaeger, X-Ray, etc.).

### Logs with trace context

When tracing is enabled, pydynox logs automatically include `trace_id` and `span_id`. This helps correlate logs with spans in your tracing backend.

```python
from pydynox import enable_tracing

enable_tracing()

# Logs now include trace context
user.save()
# INFO:pydynox:put_item table=users duration_ms=8.2 wcu=1.0 trace_id=abc123... span_id=def456...
```

With a custom logger like AWS Lambda Powertools:

```python
from aws_lambda_powertools import Logger
from pydynox import enable_tracing, set_logger

logger = Logger()
set_logger(logger)
enable_tracing()

# Powertools logs include trace_id and span_id as structured fields
user.save()
```

## Next steps

- [Async support](async.md) - Async/await for high-concurrency apps
- [Rate limiting](rate-limiting.md) - Control throughput
- [Exceptions](exceptions.md) - Error handling
