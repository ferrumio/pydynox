# Batch operations

Work with multiple items at once. Instead of making 100 separate API calls, batch operations let you send items in groups.

## Key features

- `sync_batch_get` / `batch_get` - Fetch up to 100 items per request (auto-splits larger batches)
- `SyncBatchWriter` / `BatchWriter` - Write up to 25 items per request (auto-splits larger batches)
- Automatic retry for failed items
- Mix puts and deletes in one batch
- Async-first API: `BatchWriter` and `batch_get` are async by default
- Metrics on every operation (see [observability](observability.md))

## Getting started

### Batch get

Fetch multiple items by their keys. DynamoDB limits batch gets to 100 items per request, but pydynox handles larger batches automatically.

=== "batch_get.py"
    ```python
    --8<-- "docs/examples/batch/batch_get.py"
    ```

Items are returned in any order (not guaranteed to match input order). Missing items are silently skipped.

### Batch write

Use `BatchWriter` to save or delete many items. The batch writer handles all the complexity for you: it groups items into batches, sends them to DynamoDB, and retries any items that fail.

=== "batch_write.py"
    ```python
    --8<-- "docs/examples/batch/batch_write.py"
    ```

When you use `BatchWriter` as a context manager (with `with`), it automatically flushes any remaining items when the block ends. This means you don't have to worry about items being left unsent.

The batch writer accepts two types of operations:

- `batch.put(item)` - Add or replace an item
- `batch.delete(key)` - Remove an item by its key

You can mix both operations in the same batch. DynamoDB processes them in any order, so don't rely on a specific sequence.

## Advanced

### Manual flush

By default, the batch writer sends items to DynamoDB when it has 25 items ready, or when the context exits. If you want to send items earlier, call `flush()`:

```python
with BatchWriter(client, "users") as batch:
    for i in range(100):
        batch.put({"pk": f"USER#{i}", "name": f"User {i}"})
        
        # Flush every 50 items instead of waiting
        if i % 50 == 0:
            batch.flush()
```

This is useful when you want to see progress during long-running operations, or when you need to free up memory.

### Error handling

DynamoDB sometimes can't process all items in a batch. This happens when you hit throughput limits or when there's a temporary service issue.

The batch writer automatically retries failed items with exponential backoff. If items still fail after all retries, an exception is raised when the context exits:

```python
try:
    with BatchWriter(client, "users") as batch:
        batch.put({"pk": "USER#1", "name": "John"})
except Exception as e:
    print(f"Some items failed: {e}")
```

!!! tip
    If you're seeing frequent failures, consider using [rate limiting](rate-limiting.md) to stay within your provisioned capacity.

### Async batch operations

All batch operations have async versions. Use `AsyncBatchWriter` for writes and `async_batch_get` for reads:

=== "async_batch.py"
    ```python
    --8<-- "docs/examples/batch/async_batch.py"
    ```

The async versions work the same as sync, but use `async with` and `await`.

### Performance tips

1. **Use batch operations for bulk work** - If you're saving more than a few items, batching is faster than individual `put_item` calls.

2. **Use `as_dict=True` for read-heavy workloads** - Skip model instantiation when you just need the data.

3. **Don't batch single items** - For one or two items, use regular `put_item` or `get_item`. The overhead of batching isn't worth it.

4. **Consider rate limiting** - If you're writing a lot of data, combine batch operations with rate limiting to avoid throttling.


## Testing your code

Test batch operations without DynamoDB using the built-in memory backend:

=== "testing_batch.py"
    ```python
    --8<-- "docs/examples/batch/testing_batch.py"
    ```

No setup needed. Just add `pydynox_memory_backend` to your test function. See [Testing](testing.md) for more details.

## Next steps

- [Transactions](transactions.md) - All-or-nothing operations
- [Rate limiting](rate-limiting.md) - Control throughput for bulk operations
- [Observability](observability.md) - Track metrics on batch operations
