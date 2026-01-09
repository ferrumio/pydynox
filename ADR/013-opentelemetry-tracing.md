# ADR 013: OpenTelemetry tracing integration

## Status

Accepted

## Context

pydynox already has built-in observability: metrics on every operation, automatic logging, and correlation IDs. But users want distributed tracing to see how DynamoDB calls fit into their larger request flow.

Many tracing solutions exist: AWS X-Ray, Jaeger, Zipkin, Datadog, etc. Each has its own API. Supporting all of them would be a maintenance nightmare.

## Decision

Use OpenTelemetry (OTEL) as the tracing standard.

### Why OpenTelemetry

1. **Vendor neutral** - One API works with X-Ray, Jaeger, Zipkin, Datadog, and others
2. **Industry standard** - CNCF graduated project, widely adopted
3. **Python support** - Mature `opentelemetry-api` package
4. **No lock-in** - Users choose their backend, we just create spans

### Why semantic conventions

We follow [OTEL Database Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/database/database-spans/) for span attributes.

**Why follow conventions:**
- Tools like Jaeger and Grafana understand these attributes
- Dashboards and alerts work out of the box
- Users don't need to learn pydynox-specific attributes

### Why `start_as_current_span`

We use `tracer.start_as_current_span()` instead of `tracer.start_span()`.

**The difference:**
- `start_span()` creates a standalone span with no parent
- `start_as_current_span()` creates a span as child of the current active span

**Why it matters:**

With `start_span()`, the DynamoDB spans would be orphans. With `start_as_current_span()`, they correctly appear as children in the trace tree.

This enables:
- Full request tracing from HTTP → Lambda → DynamoDB
- Correct parent-child relationships in Jaeger/X-Ray
- Shared `trace_id` across all spans in a request

### Why optional dependency

OpenTelemetry is an optional dependency. Users who don't need tracing don't pay for it (install time, Lambda size).

## Reasons

1. **Vendor neutral** - Works with any OTEL-compatible backend
2. **Standard attributes** - Tools understand the spans without configuration
3. **Context propagation** - Spans connect to parent spans automatically
4. **Optional** - Zero cost for users who don't need it

## Alternatives considered

- **AWS X-Ray only** - Locks users into X-Ray, doesn't work with Jaeger/Datadog
- **Custom tracing API** - Users would need adapters for each backend
- **No tracing** - Users asked for it, it's a common need
- **`start_span()` without context** - Breaks parent-child relationships

## Consequences

- Users can trace DynamoDB calls in their distributed systems
- Spans appear correctly in trace trees (parent-child)
- Standard attributes work with existing dashboards
- Optional dependency keeps Lambda size small
- Users must install `opentelemetry-api` to use tracing
