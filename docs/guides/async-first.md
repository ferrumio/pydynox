# We are async-first

pydynox supports async natively. Every operation has an async version, and we recommend using async for new projects.

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
3. Rust runs the DynamoDB call using tokio (async runtime)
4. Python is free to run other code while Rust waits for DynamoDB
5. When DynamoDB responds, Rust reacquires the GIL and returns the result

This means pydynox async operations are truly non-blocking. The GIL is released during the entire network call.

```
Python                    Rust                      DynamoDB
  |                         |                          |
  |-- async_get() --------->|                          |
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
    User.get(pk=user_id)  # 50ms each
print(f"Sync: {time.perf_counter() - start:.2f}s")
# Output: Sync: 0.52s (10 × 50ms = 500ms)

# Async: all at once
start = time.perf_counter()
await asyncio.gather(*[User.async_get(pk=uid) for uid in user_ids])
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
    await user.async_save()

    # Read
    user = await User.async_get(pk="USER#123")

    # Query
    async for user in User.async_query(hash_key="USER#123"):
        print(user.name)

    # Delete
    await user.async_delete()
```

## Async methods

Every sync method has an async version with `async_` prefix:

| Sync | Async |
|------|-------|
| `model.save()` | `await model.async_save()` |
| `model.delete()` | `await model.async_delete()` |
| `model.update()` | `await model.async_update()` |
| `Model.get()` | `await Model.async_get()` |
| `Model.query()` | `Model.async_query()` |
| `Model.scan()` | `Model.async_scan()` |
| `Model.batch_get()` | `await Model.async_batch_get()` |
| `BatchWriter` | `AsyncBatchWriter` |

## Concurrent operations

Run multiple operations at the same time:

```python
import asyncio

async def get_user_with_orders(user_id: str):
    # Both calls run concurrently - total time is max(user_time, orders_time)
    user, orders = await asyncio.gather(
        User.async_get(pk=user_id),
        Order.async_query(hash_key=user_id).collect(),
    )
    return user, orders
```

## When to use sync

Sync is fine for:

- Scripts and CLI tools
- Simple Lambda functions
- Code that doesn't need concurrency

```python
# Sync works too
user = User.get(pk="USER#123")
user.name = "Jane"
user.save()
```

Sync methods also release the GIL during the network call, so they won't block other Python threads.

## Next steps

- [Async support](async.md) - Full async guide
- [Models](models.md) - CRUD operations
- [Query](query.md) - Query items
