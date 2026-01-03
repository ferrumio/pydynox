# Auto-generate strategies

Generate IDs and timestamps automatically when saving items.

## Key features

- Generate UUIDs, ULIDs, KSUIDs for unique identifiers
- Generate timestamps in epoch or ISO 8601 format
- Values generated on `save()` only when attribute is `None`
- Thread-safe for concurrent async operations
- Fast Rust implementation

## Getting started

Use `AutoGenerate` as the default value for an attribute. The value is generated when you call `save()`.

=== "basic_usage.py"
    ```python
    --8<-- "docs/examples/generators/basic_usage.py"
    ```

## Available strategies

| Strategy | Output type | Example | Use case |
|----------|-------------|---------|----------|
| `UUID4` | str (36 chars) | `"550e8400-e29b-41d4-a716-446655440000"` | Standard unique ID |
| `ULID` | str (26 chars) | `"01ARZ3NDEKTSV4RRFFQ69G5FAV"` | Sortable ID (recommended) |
| `KSUID` | str (27 chars) | `"0ujsswThIGTUYm2K8FjOOfXtY1K"` | K-Sortable ID |
| `EPOCH` | int | `1704067200` | Unix timestamp (seconds) |
| `EPOCH_MS` | int | `1704067200000` | Unix timestamp (milliseconds) |
| `ISO8601` | str (20 chars) | `"2024-01-01T00:00:00Z"` | Human-readable timestamp |

### Choosing an ID strategy

| Need | Use | Why |
|------|-----|-----|
| Sortable by time | `ULID` | Lexicographically sortable, good for range queries |
| Standard format | `UUID4` | Widely recognized, 128-bit random |
| Compact + sortable | `KSUID` | 27 chars, time-sortable, base62 encoded |

`ULID` is recommended for partition keys. Items created later have higher IDs, which helps with debugging and range queries.

### Choosing a timestamp strategy

| Need | Use | Why |
|------|-----|-----|
| Numeric comparisons | `EPOCH` or `EPOCH_MS` | Easy to compare, filter, sort |
| Human readable | `ISO8601` | Easy to read in logs and debugging |
| High precision | `EPOCH_MS` | Millisecond accuracy |

## Using multiple strategies

You can use different strategies on different fields:

=== "all_strategies.py"
    ```python
    --8<-- "docs/examples/generators/all_strategies.py"
    ```

## Skipping auto-generation

If you provide a value, auto-generation is skipped:

=== "skip_generation.py"
    ```python
    --8<-- "docs/examples/generators/skip_generation.py"
    ```

## Async and concurrency

Auto-generate is thread-safe. You can create many items concurrently and each will get a unique ID:

=== "async_usage.py"
    ```python
    --8<-- "docs/examples/generators/async_usage.py"
    ```

## When values are generated

Values are generated at `save()` time, not at model creation:

```python
order = Order(sk="DATA")
print(order.pk)  # None - not generated yet

order.save()
print(order.pk)  # "01ARZ3NDEKTSV4RRFFQ69G5FAV" - generated now
```

This means:

- You can check if `pk is None` before save
- The timestamp reflects save time, not creation time
- Multiple saves don't regenerate (value is no longer None)

## Combining with hooks

Use `before_save` hooks if you need custom logic:

```python
from pydynox import AutoGenerate, Model, ModelConfig
from pydynox.attributes import StringAttribute
from pydynox.hooks import before_save


class AuditLog(Model):
    model_config = ModelConfig(table="audit")

    pk = StringAttribute(hash_key=True, default=AutoGenerate.ULID)
    sk = StringAttribute(range_key=True)
    created_at = StringAttribute(default=AutoGenerate.ISO8601)
    created_by = StringAttribute()

    @before_save
    def set_sk(self):
        if self.sk is None:
            self.sk = f"LOG#{self.created_at}"
```

!!! note
    Auto-generate runs after `before_save` hooks. If you need the generated value in a hook, use `generate_value()` from `pydynox.generators`.

## Common patterns

### Order with auto ID and timestamp

```python
from pydynox import AutoGenerate, Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute


class Order(Model):
    model_config = ModelConfig(table="orders")

    pk = StringAttribute(hash_key=True, default=AutoGenerate.ULID)
    sk = StringAttribute(range_key=True)
    created_at = StringAttribute(default=AutoGenerate.ISO8601)
    total = NumberAttribute()


order = Order(sk="ORDER#DETAILS", total=99.99)
order.save()
# pk and created_at are auto-generated
```

### Event sourcing with ULID

ULIDs are great for event sourcing because they're time-sortable:

```python
class Event(Model):
    model_config = ModelConfig(table="events")

    pk = StringAttribute(hash_key=True)  # Aggregate ID
    sk = StringAttribute(range_key=True, default=AutoGenerate.ULID)
    event_type = StringAttribute()
    data = MapAttribute()


# Events for the same aggregate sort by creation time
event1 = Event(pk="ORDER#123", event_type="OrderCreated", data={...})
event1.save()

event2 = Event(pk="ORDER#123", event_type="OrderShipped", data={...})
event2.save()

# Query returns events in order: event1, event2
```

### Session with expiration

```python
from pydynox.attributes import TTLAttribute, ExpiresIn


class Session(Model):
    model_config = ModelConfig(table="sessions")

    pk = StringAttribute(hash_key=True, default=AutoGenerate.UUID4)
    sk = StringAttribute(range_key=True)
    created_at = NumberAttribute(default=AutoGenerate.EPOCH)
    expires_at = TTLAttribute()


session = Session(sk="SESSION#DATA", expires_at=ExpiresIn.hours(24))
session.save()
```


## Next steps

- [Rate limiting](rate-limiting.md) - Control throughput
- [Hooks](hooks.md) - Run code before/after operations
- [Attributes](attributes.md) - All attribute types
