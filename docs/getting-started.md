# Getting started

This guide walks you through installing pydynox and creating your first model. By the end, you'll have a working DynamoDB model with CRUD operations.

## Key features

- Install with pip or uv
- Define models with typed attributes
- CRUD operations with simple methods
- Local development with DynamoDB Local

## Installation

=== "pip"
    ```bash
    pip install pydynox
    ```

=== "uv"
    ```bash
    uv add pydynox
    ```

To verify the installation:

```python
import pydynox
print(pydynox.__version__)
# 0.1.0

# For detailed version info
print(pydynox.version_info())
#        pydynox version: 0.1.0
#        python version: 3.11.0
#               platform: macOS-14.0-arm64
#       related packages: boto3-1.34.0 pydantic-2.5.0
```

## Your first model

Let's create a simple User model. A model is a Python class that represents items in a DynamoDB table.

=== "basic_model.py"
    ```python
    --8<-- "docs/examples/models/basic_model.py"
    ```

Here's what each part does:

- `model_config = ModelConfig(table="users")` - Configuration for the model. `table` is the DynamoDB table name.
- `pk = StringAttribute(hash_key=True)` - The partition key. Every item needs one.
- `sk = StringAttribute(range_key=True)` - The sort key. Optional, but useful for complex access patterns.
- Other attributes - Regular fields with their types and optional defaults.

## Async-first

Python async is growing. FastAPI, aiohttp, Starlette - modern web frameworks are async. pydynox follows this trend.

Every async method has a sync version with `sync_` prefix:

| Async (default) | Sync |
|-----------------|------|
| `await user.save()` | `user.sync_save()` |
| `await User.get()` | `User.sync_get()` |
| `await user.delete()` | `user.sync_delete()` |
| `async for x in User.query()` | `for x in User.sync_query()` |

Both versions release the GIL during network calls. The difference: async lets you run multiple operations at the same time with `asyncio.gather()`. Sync runs one after another.

For the full story on why async matters and how pydynox handles it, see [Async-first](guides/async-first.md).

## Basic operations

Now let's use the model to work with DynamoDB. pydynox uses an async-first API - methods without prefix are async (default), methods with `sync_` prefix are sync.

=== "Async (default)"
    ```python
    --8<-- "docs/examples/models/crud_operations.py"
    ```

=== "Sync (use sync_ prefix)"
    ```python
    --8<-- "docs/examples/models/sync_crud_operations.py"
    ```

### Create

Instantiate your model and call `save()`:

```python
user = User(pk="USER#123", sk="PROFILE", name="John", age=30)
await user.save()  # async
user.sync_save()   # sync
```

### Read

Use `get()` with the key attributes:

```python
# Async
user = await User.get(pk="USER#123", sk="PROFILE")
if user:
    print(user.name)

# Sync
user = User.sync_get(pk="USER#123", sk="PROFILE")
```

### Update

Change attributes and save, or use `update()` for partial updates:

```python
# Full update (async)
user.name = "Jane"
await user.save()

# Partial update (async)
await user.update(name="Jane", age=31)

# Sync versions
user.sync_save()
user.sync_update(name="Jane", age=31)
```

### Delete

Call `delete()` on an instance:

```python
await user.delete()  # async
user.sync_delete()   # sync
```

## Configuration

`ModelConfig` configures how your model connects to DynamoDB:

```python
from pydynox import Model, ModelConfig

class User(Model):
    model_config = ModelConfig(
        table="users",              # Required - table name
        region="us-east-1",         # Optional - AWS region
        endpoint_url=None,          # Optional - for local testing
    )
```

## Local development

### Memory backend (recommended for tests)

pydynox has a built-in memory backend. No Docker, no setup - just a pytest fixture:

```python
import pytest
from pydynox.testing import memory_backend

@pytest.fixture
def dynamo():
    with memory_backend():
        yield

def test_create_user(dynamo):
    user = User(pk="USER#123", name="John")
    user.sync_save()
    
    found = User.sync_get(pk="USER#123")
    assert found.name == "John"
```

The memory backend is fast and isolated. Each test starts with a clean slate.

For more details, see [Testing](guides/testing.md).

### DynamoDB Local

For integration tests that need real DynamoDB behavior, use [DynamoDB Local](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DynamoDBLocal.html):

```bash
docker run -p 8000:8000 amazon/dynamodb-local
```

Then point your model to it:

```python
from pydynox import Model, ModelConfig

class User(Model):
    model_config = ModelConfig(
        table="users",
        endpoint_url="http://localhost:8000",
    )
```

## Next steps

Now that you have the basics working:

- [Models](guides/models.md) - Learn about all attribute types and options
- [Batch operations](guides/batch.md) - Work with multiple items efficiently
- [Rate limiting](guides/rate-limiting.md) - Control throughput to avoid throttling
- [Lifecycle hooks](guides/hooks.md) - Add validation and logging
