# Async support

pydynox is async-first. All main operations like `batch_get`, `batch_write`, and `BatchWriter` are async by default. This works great with FastAPI, aiohttp, and other asyncio-based frameworks.

## Why async?

Sync operations block the event loop:

```python
async def handle_request(user_id: str):
    user = User.sync_get(pk=user_id, sk="PROFILE")  # Blocks!
    # Other async tasks can't run while waiting for DynamoDB
```

Async operations let other tasks run while waiting for I/O:

```python
async def handle_request(user_id: str):
    user = await User.get(pk=user_id, sk="PROFILE")  # Non-blocking
    # Other tasks can run while waiting
```

## Model async methods

Model CRUD operations are async by default:

=== "model_async.py"
    ```python
    --8<-- "docs/examples/async/model_async.py"
    ```

## Client async methods

The `DynamoDBClient` methods are also async by default:

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

## Sync operations

For sync code (scripts, CLI tools, or frameworks that don't support async), use the `sync_` prefixed methods:

```python
# Sync versions have sync_ prefix
user = User.sync_get(pk="USER#1", sk="PROFILE")
user.sync_save()
user.sync_delete()

# Client sync methods
client.sync_put_item("users", item)
client.sync_get_item("users", key)
items = client.sync_batch_get("users", keys)
```

## API reference

### Model methods

| Async (default) | Sync |
|-----------------|------|
| `await Model.get()` | `Model.sync_get()` |
| `await model.save()` | `model.sync_save()` |
| `await model.delete()` | `model.sync_delete()` |
| `await model.update()` | `model.sync_update()` |
| `await Model.batch_get()` | `Model.sync_batch_get()` |
| `async for item in Model.query()` | `for item in Model.sync_query()` |
| `async for item in Model.scan()` | `for item in Model.sync_scan()` |

### DynamoDBClient methods

| Async (default) | Sync |
|-----------------|------|
| `await client.get_item()` | `client.sync_get_item()` |
| `await client.put_item()` | `client.sync_put_item()` |
| `await client.delete_item()` | `client.sync_delete_item()` |
| `await client.update_item()` | `client.sync_update_item()` |
| `async for item in client.query()` | `for item in client.sync_query()` |
| `await client.batch_get()` | `client.sync_batch_get()` |
| `await client.batch_write()` | `client.sync_batch_write()` |

### Batch operations

| Async (default) | Sync |
|-----------------|------|
| `async with BatchWriter()` | `with SyncBatchWriter()` |

## Notes

- Async methods use the same Rust core as sync methods
- No extra dependencies needed
- Works with any asyncio event loop
- Hooks still run synchronously (before/after save, etc.)


## Next steps

- [Batch operations](batch.md) - Work with multiple items at once
- [Transactions](transactions.md) - All-or-nothing operations
- [Query](query.md) - Query items with async support
