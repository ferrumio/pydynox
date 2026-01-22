# Async support

pydynox supports async/await for high-concurrency applications like FastAPI, aiohttp, and other asyncio-based frameworks.

## Why async?

Sync operations block the event loop:

```python
async def handle_request(user_id: str):
    user = User.get(pk=user_id, sk="PROFILE")  # Blocks!
    # Other async tasks can't run while waiting for DynamoDB
```

Async operations let other tasks run while waiting for I/O:

```python
async def handle_request(user_id: str):
    user = await User.async_get(pk=user_id, sk="PROFILE")  # Non-blocking
    # Other tasks can run while waiting
```

## Model async methods

All Model CRUD operations have async versions with `async_` prefix:

=== "model_async.py"
    ```python
    --8<-- "docs/examples/async/model_async.py"
    ```

## Client async methods

The `DynamoDBClient` also has async versions:

=== "client_async.py"
    ```python
    --8<-- "docs/examples/async/client_async.py"
    ```

## Async query

Query returns an async iterator:

=== "query_async.py"
    ```python
    --8<-- "docs/examples/async/query_async.py"
    ```

## Concurrent operations

The real power of async is running operations concurrently:

=== "concurrent.py"
    ```python
    --8<-- "docs/examples/async/concurrent.py"
    ```

## Real world example

Fetch user and their orders at the same time:

=== "real_world.py"
    ```python
    --8<-- "docs/examples/async/real_world.py"
    ```

## FastAPI example

=== "fastapi_example.py"
    ```python
    --8<-- "docs/examples/async/fastapi_example.py"
    ```

## Available async methods

### Model

| Sync | Async |
|------|-------|
| `Model.get()` | `Model.async_get()` |
| `model.save()` | `model.async_save()` |
| `model.delete()` | `model.async_delete()` |
| `model.update()` | `model.async_update()` |
| `Model.batch_get()` | `Model.async_batch_get()` |
| `Model.query()` | `Model.async_query()` |
| `Model.scan()` | `Model.async_scan()` |

### DynamoDBClient

| Sync | Async |
|------|-------|
| `get_item()` | `async_get_item()` |
| `put_item()` | `async_put_item()` |
| `delete_item()` | `async_delete_item()` |
| `update_item()` | `async_update_item()` |
| `query()` | `async_query()` |
| `batch_get()` | `async_batch_get()` |
| `batch_write()` | `async_batch_write()` |

### Batch operations

| Sync | Async |
|------|-------|
| `BatchWriter` | `AsyncBatchWriter` |

## Notes

- Async methods use the same Rust core as sync methods
- No extra dependencies needed
- Works with any asyncio event loop
- Hooks still run synchronously (before/after save, etc.)


## Next steps

- [Batch operations](batch.md) - Work with multiple items at once
- [Transactions](transactions.md) - All-or-nothing operations
- [Query](query.md) - Query items with async support
