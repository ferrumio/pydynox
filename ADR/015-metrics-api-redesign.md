# ADR 015: Metrics API Redesign

## Status

Accepted

## Context

The original metrics API used instance attributes:

```python
user.save()
print(user.metrics.duration_ms)  # Instance attribute
```

This had a problem: `.metrics` could conflict with user-defined fields. If someone had a `metrics` field in their model, it would break.

```python
class Order(Model):
    pk = StringAttribute(hash_key=True)
    metrics = MapAttribute()  # Conflict!
```

## Decision

Use class methods instead of instance attributes:

**Model API:**
```python
user.save()
User.get_last_metrics()   # Last operation
User.get_total_metrics()  # All operations combined
User.reset_metrics()      # Clear metrics
```

**Client API:**
```python
client.put_item(...)
client.get_last_metrics()   # Last operation
client.get_total_metrics()  # All operations combined
client.reset_metrics()      # Clear metrics
```

## Reason

1. **No field conflicts** - Class methods don't clash with instance attributes
2. **Linear experience** - Same API for Model and Client
3. **Total metrics** - Can track metrics across multiple operations
4. **Thread-safe** - Uses thread-local storage for metrics

## Metrics Structure

```python
@dataclass
class ModelMetrics:
    duration_ms: float
    read_units: float
    write_units: float
    item_count: int
    scanned_count: int
    retries: int
    kms_duration_ms: float  # Time spent on KMS calls
    kms_calls: int          # Number of KMS API calls
```

## Special Case: PartiQL

PartiQL returns a list of items. It keeps the `.metrics` attribute on the result:

```python
result = client.execute_partiql("SELECT * FROM users")
print(result.metrics)  # ListWithMetrics has .metrics
```

This is fine because `ListWithMetrics` is a pydynox class, not a user model.

## Consequences

- No backward compatibility with old `.metrics` attribute
- Users must update code to use new methods
- Cleaner API with no naming conflicts
- Better support for aggregated metrics

