# Async-first design

pydynox is async-first. This means:

1. Every sync method has an async version with `async_` prefix
2. Async and sync APIs must have feature parity
3. New features start with async, then add sync
4. Docs show async examples first, sync as alternative

## Why async-first?

Python has a GIL (Global Interpreter Lock). Only one thread runs Python code at a time. Async lets Python do other work while waiting for I/O.

pydynox is written in Rust. When you call an async method:

1. Python calls Rust via PyO3
2. Rust releases the GIL immediately
3. Rust runs the DynamoDB call using tokio
4. Python is free to run other coroutines
5. When done, Rust reacquires the GIL and returns

This means pydynox async operations are truly non-blocking.

## API parity checklist

When adding a new feature, ensure both sync and async versions have:

- Same method signature (except `async_` prefix)
- Same return type (or async equivalent)
- Same properties (e.g., `last_evaluated_key` on query results)
- Same behavior

## Async method naming

| Sync | Async |
|------|-------|
| `model.save()` | `model.async_save()` |
| `model.delete()` | `model.async_delete()` |
| `model.update()` | `model.async_update()` |
| `Model.get()` | `Model.async_get()` |
| `Model.query()` | `Model.async_query()` |
| `Model.scan()` | `Model.async_scan()` |
| `Model.batch_get()` | `Model.async_batch_get()` |
| `BatchWriter` | `AsyncBatchWriter` |
| `client.put_item()` | `client.async_put_item()` |
| `client.get_item()` | `client.async_get_item()` |

## Result classes

Async results are separate classes but must have same properties:

- `ModelQueryResult` / `AsyncModelQueryResult`
- `ModelScanResult` / `AsyncModelScanResult`
- `GSIQueryResult` / `AsyncGSIQueryResult`
- `LSIQueryResult` / `AsyncLSIQueryResult`

All must expose `last_evaluated_key` for pagination.

## Testing

Every async feature needs tests. See `tests/integration/async_ops/` for examples.

## See also

- ADR 018: Async-first design
- docs/guides/async-first.md
