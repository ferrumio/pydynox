# ADR 019: Release GIL during sync block_on calls

## Status

Accepted

## Context

pydynox has both sync and async APIs. Sync operations use `runtime.block_on(...)` to run async code on the Tokio runtime. The problem: `block_on` blocks the current thread while waiting for the network call to finish. During that time, the Python GIL is held.

This means:

1. Other Python threads can't run while a sync DynamoDB call is in progress
2. In multi-threaded Python apps, one slow DynamoDB call blocks all threads
3. The S3 operations already used `py.detach()` to release the GIL, but DynamoDB operations did not

This is especially bad for web servers like Flask or Django that use thread pools. One slow query blocks the entire thread, and the GIL prevents other threads from making progress.

## Decision

Wrap all sync `runtime.block_on(...)` calls with `py.detach(|| ...)` to release the GIL during network I/O.

### Before

```rust
let result = runtime.block_on(execute_get_item(client.clone(), prepared));
```

### After

```rust
let result = py.detach(|| runtime.block_on(execute_get_item(client.clone(), prepared)));
```

`py.detach()` releases the GIL before calling the closure, and reacquires it when the closure returns. The `execute_*` functions are pure Rust with no Python types, so they don't need the GIL.

### What changed

13 sync functions across 11 files:

- `sync_put_item` (basic_operations/put.rs)
- `sync_get_item` (basic_operations/get.rs)
- `sync_delete_item` (basic_operations/delete.rs)
- `sync_update_item` (basic_operations/update_op.rs)
- `sync_query` (basic_operations/query.rs)
- `sync_scan` (basic_operations/scan.rs)
- `sync_count` (basic_operations/scan.rs)
- `sync_parallel_scan` (basic_operations/scan.rs)
- `sync_execute_statement` (basic_operations/partiql.rs)
- `sync_batch_write` (batch_operations/write.rs)
- `sync_batch_get` (batch_operations/get.rs)
- `sync_transact_write` (transaction_operations/write.rs)
- `sync_transact_get` (transaction_operations/get.rs)

### Why this works with prepare/execute

The prepare/execute pattern (ADR 011) makes this safe. The three phases are:

1. **Prepare** — needs GIL (converts Python types to Rust)
2. **Execute** — does NOT need GIL (pure Rust + network I/O)
3. **Convert** — needs GIL (converts Rust types back to Python)

We only release the GIL during phase 2. Phases 1 and 3 still hold it.

## Reasons

1. **Thread safety** — Other Python threads can run during DynamoDB calls
2. **Better throughput** — Multi-threaded apps (Flask, Django) benefit directly
3. **Consistency** — S3 operations already did this. DynamoDB should too
4. **No cost** — Releasing and reacquiring the GIL is cheap (~100ns)

## Alternatives considered

### Do nothing

Leave the GIL held during sync calls. This is simpler but hurts multi-threaded apps. Users would need to use async to get concurrency.

### Release GIL inside execute_* functions

Move the `py.detach()` inside the execute functions. Rejected because execute functions don't have access to `py` — they are pure Rust by design (ADR 011).

## Consequences

### Positive

- Multi-threaded Python apps get better throughput
- Consistent with S3 operations
- No API changes — fully backward compatible
- No new dependencies

### Negative

- None observed. All 661 unit tests, 658 integration tests, and 193 examples pass without changes.
