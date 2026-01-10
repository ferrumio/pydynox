# ADR 014: as_dict parameter for query/scan operations

## Status

Accepted

## Context

pydynox returns Model instances from query/scan operations. This gives users type hints, methods like `.save()` and `.delete()`, and hooks like `after_load`.

But creating Python objects is slow. For each item returned from DynamoDB:
1. Rust deserializes the DynamoDB response (fast)
2. Python creates a Model instance (slow)
3. Python runs `after_load` hooks (if any)

For small result sets (10-50 items), this is fine. For large result sets (hundreds or thousands), Model creation becomes a bottleneck.

This is how Python works. Object creation has overhead. There's no way to make it faster in Python itself.

## Decision

Add `as_dict=True` parameter to query/scan/get operations. When enabled, skip Model instantiation and return plain Python dicts.

### Where it applies

- `Model.get()` / `Model.async_get()`
- `Model.query()` / `Model.async_query()`
- `Model.scan()` / `Model.async_scan()`
- `Model.parallel_scan()` / `Model.async_parallel_scan()`
- `Model.batch_get()`

### Default behavior

`as_dict=False` by default. Users get Model instances unless they ask for dicts.

## Reasons

1. **Python overhead is real** - Object creation is slow, we can't fix Python
2. **User choice** - Let users trade features for speed when they need it
3. **Fair comparison** - boto3 and PynamoDB return dicts, now pydynox can too
4. **Read-only use cases** - Many queries just read data, don't need `.save()`

## Trade-offs

| | Model instances | `as_dict=True` |
|---|---|---|
| Speed | Slower | Faster |
| Memory | More | Less |
| Type hints | Full IDE support | Dict access |
| Methods | `.save()`, `.delete()` | None |
| Hooks | `after_load` runs | No hooks |
| Validation | Attribute types enforced | Raw DynamoDB types |

## Alternatives considered

- **Always return dicts** - Breaks the ORM pattern, loses type safety
- **Lazy Model creation** - Complex, still creates objects eventually
- **Rust-side Model creation** - PyO3 can't create Python classes efficiently
- **Do nothing** - Users asked for this, it's a real bottleneck

## Validation

We added tests and benchmarks to validate this decision:

**Memory tests** (`tests/memory/test_as_dict_memory.py`):
- Query 500 items: ~1.17x less memory with `as_dict`
- Batch get 100 items: ~1.55x less memory with `as_dict`
- Repeated queries show stable memory (no leaks)

**Lambda benchmark** (`benchmarks/src/pydynox/handler.py`):
- Added `query_as_dict` metric alongside regular `query`
- Allows fair comparison with boto3 and PynamoDB (both return dicts)

**Unit tests**: Added to existing test files (test_model.py, test_query.py, test_scan.py)

**Integration tests**: Added in tests/integration/operations/

## Consequences

- Users can get raw performance when needed
- Benchmarks against boto3/PynamoDB are fair
- Large data exports are faster
- Users lose Model features when using `as_dict=True`
- API is slightly more complex (one more parameter)
