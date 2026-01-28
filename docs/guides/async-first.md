# We are async-first

pydynox uses an async-first API. Methods without prefix are async (default), methods with `sync_` prefix are sync.

## Why async matters in Python

Python has a Global Interpreter Lock (GIL). Only one thread can run Python code at a time. This means:

- **Sync I/O blocks everything** - While waiting for DynamoDB, your app can't do anything else
- **Threads don't help much** - The GIL limits true parallelism
- **Async is the solution** - Your app can handle other work while waiting for I/O

With async, when you `await` a DynamoDB call, Python can run other coroutines. Your web server can handle more requests with the same resources.

!!! note "Free-threaded Python (3.13+)"
    Python 3.13 introduced experimental free-threaded mode (no GIL), and Python 3.14 improves it further. However, it requires a special build (`--disable-gil`) and many libraries don't support it yet. For now, async remains the best way to handle concurrent I/O in Python. When free-threaded Python becomes mainstream, pydynox will work even better since our Rust core already releases the GIL.

## How pydynox handles this

pydynox is written in Rust. When you call an async method:

1. Python calls into Rust via PyO3
2. Rust releases the GIL immediately
3. Rust runs the DynamoDB call using [tokio](https://tokio.rs/) (async runtime)
4. PyO3's [`future_into_py`](https://docs.rs/pyo3/latest/pyo3/coroutine/fn.future_into_py.html) bridges Python's asyncio with tokio
5. Python is free to run other code while Rust waits for DynamoDB
6. When DynamoDB responds, Rust reacquires the GIL and returns the result

This means pydynox async operations are truly non-blocking. The GIL is released during the entire network call.

```
Python                    Rust                      DynamoDB
  |                         |                          |
  |-- get() --------------->|                          |
  |   (GIL released)        |-- HTTP request --------->|
  |                         |                          |
  |   (free to run          |   (waiting, no GIL)      |
  |    other coroutines)    |                          |
  |                         |<-- HTTP response --------|
  |<-- result --------------|                          |
  |   (GIL reacquired)      |                          |
```

## The difference in practice

Here's a simple benchmark. Imagine fetching 10 users from DynamoDB, each call taking 50ms:

```python
import asyncio
import time

# Sync: one after another
start = time.perf_counter()
for user_id in user_ids:
    User.sync_get(pk=user_id)  # 50ms each
print(f"Sync: {time.perf_counter() - start:.2f}s")
# Output: Sync: 0.52s (10 × 50ms = 500ms)

# Async: all at once
start = time.perf_counter()
await asyncio.gather(*[User.get(pk=uid) for uid in user_ids])
print(f"Async: {time.perf_counter() - start:.2f}s")
# Output: Async: 0.05s (all run in parallel)
```

Result: async is 10x faster for this workload. The more concurrent calls, the bigger the gain.

## Quick example

```python
from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute

class User(Model):
    model_config = ModelConfig(table="users")
    pk = StringAttribute(hash_key=True)
    name = StringAttribute()

async def main():
    # Create
    user = User(pk="USER#123", name="John")
    await user.save()

    # Read
    user = await User.get(pk="USER#123")

    # Query
    async for user in User.query(hash_key="USER#123"):
        print(user.name)

    # Delete
    await user.delete()
```

## API pattern

Async is the default. Sync methods have `sync_` prefix.

### Model operations

| Async (default) | Sync |
|-----------------|------|
| `await model.save()` | `model.sync_save()` |
| `await model.delete()` | `model.sync_delete()` |
| `await model.update()` | `model.sync_update()` |
| `await Model.get()` | `Model.sync_get()` |
| `await Model.update_by_key()` | `Model.sync_update_by_key()` |
| `await Model.delete_by_key()` | `Model.sync_delete_by_key()` |

### Query and scan

| Async (default) | Sync |
|-----------------|------|
| `async for x in Model.query()` | `for x in Model.sync_query()` |
| `async for x in Model.scan()` | `for x in Model.sync_scan()` |
| `await Model.count()` | `Model.sync_count()` |
| `await Model.parallel_scan()` | `Model.sync_parallel_scan()` |
| `await Model.execute_statement()` | `Model.sync_execute_statement()` |

### Batch operations

| Async (default) | Sync |
|-----------------|------|
| `await Model.batch_get()` | `Model.sync_batch_get()` |
| `async with BatchWriter()` | `with SyncBatchWriter()` |
| `await client.batch_write()` | `client.sync_batch_write()` |
| `await client.batch_get()` | `client.sync_batch_get()` |

### Transactions

| Async (default) | Sync |
|-----------------|------|
| `await client.transact_write()` | `client.sync_transact_write()` |
| `await client.transact_get()` | `client.sync_transact_get()` |

### Table operations

| Async (default) | Sync |
|-----------------|------|
| `await Model.create_table()` | `Model.sync_create_table()` |
| `await Model.table_exists()` | `Model.sync_table_exists()` |
| `await Model.delete_table()` | `Model.sync_delete_table()` |
| `await client.create_table()` | `client.sync_create_table()` |
| `await client.table_exists()` | `client.sync_table_exists()` |
| `await client.delete_table()` | `client.sync_delete_table()` |
| `await client.wait_for_table_active()` | `client.sync_wait_for_table_active()` |

### Client CRUD

| Async (default) | Sync |
|-----------------|------|
| `await client.put_item()` | `client.sync_put_item()` |
| `await client.get_item()` | `client.sync_get_item()` |
| `await client.delete_item()` | `client.sync_delete_item()` |
| `await client.update_item()` | `client.sync_update_item()` |
| `await client.query()` | `client.sync_query()` |
| `await client.scan()` | `client.sync_scan()` |
| `await client.count()` | `client.sync_count()` |
| `await client.parallel_scan()` | `client.sync_parallel_scan()` |

### S3 attribute

| Async (default) | Sync |
|-----------------|------|
| `await s3_value.get_bytes()` | `s3_value.sync_get_bytes()` |
| `await s3_value.save_to()` | `s3_value.sync_save_to()` |
| `await s3_value.presigned_url()` | `s3_value.sync_presigned_url()` |

### Index queries

| Async (default) | Sync |
|-----------------|------|
| `async for x in index.query()` | `for x in index.sync_query()` |

## Concurrent operations

Run multiple operations at the same time:

```python
import asyncio

async def get_user_with_orders(user_id: str):
    # Both calls run concurrently - total time is max(user_time, orders_time)
    user, orders = await asyncio.gather(
        User.get(pk=user_id),
        Order.query(hash_key=user_id).all(),
    )
    return user, orders
```

## When to use sync

Sync is fine for:

- Scripts and CLI tools
- Simple Lambda functions
- Code that doesn't need concurrency

```python
# Sync works too - use sync_ prefix
user = User.sync_get(pk="USER#123")
user.name = "Jane"
user.sync_save()
```

Sync methods also release the GIL during the network call, so they won't block other Python threads.

## Next steps

- [Models](models.md) - CRUD operations
- [Query](query.md) - Query items
- [Batch operations](batch.md) - Batch write and get
