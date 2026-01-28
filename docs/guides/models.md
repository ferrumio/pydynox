# Models

Models define the structure of your DynamoDB items and provide CRUD operations.

## Key features

- Typed attributes with defaults
- Hash key and range key support
- Required fields with `required=True`
- Save, get, update, delete operations
- Convert to/from dict

## Getting started

### Basic model

=== "basic_model.py"
    ```python
    --8<-- "docs/examples/models/basic_model.py"
    ```

!!! tip
    Want to see all supported attribute types? Check out the [Attribute types](attributes.md) guide.

### Keys

Every model needs at least a hash key (partition key):

```python
class User(Model):
    model_config = ModelConfig(table="users")
    
    pk = StringAttribute(hash_key=True)  # Required
```

Add a range key (sort key) for composite keys:

```python
class User(Model):
    model_config = ModelConfig(table="users")
    
    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)  # Optional
```

### Defaults and required fields

=== "with_defaults.py"
    ```python
    --8<-- "docs/examples/models/with_defaults.py"
    ```

## CRUD operations

pydynox uses an async-first API. Methods without prefix are async (default), methods with `sync_` prefix are sync.

=== "Async (default)"
    ```python
    --8<-- "docs/examples/models/crud_operations.py"
    ```

=== "Sync (use sync_ prefix)"
    ```python
    --8<-- "docs/examples/models/sync_crud_operations.py"
    ```

### Create

To create a new item, instantiate your model and call `save()`:

```python
user = User(pk="USER#123", sk="PROFILE", name="John", age=30)
await user.save()  # async
user.sync_save()   # sync
```

If an item with the same key already exists, `save()` replaces it completely. This is how DynamoDB works - there's no separate "create" vs "update" at the API level.

### Read

To get an item by its key, use the class method `get()`:

```python
# Async
user = await User.get(pk="USER#123", sk="PROFILE")
if user:
    print(user.name)
else:
    print("User not found")

# Sync
user = User.sync_get(pk="USER#123", sk="PROFILE")
```

`get()` returns `None` if the item doesn't exist. Always check for `None` before using the result.

If your table has only a hash key (no range key), you only need to pass the hash key:

```python
user = await User.get(pk="USER#123")
```

#### Consistent reads

By default, `get()` uses eventually consistent reads. For strongly consistent reads, use `consistent_read=True`:

=== "Async (default)"
    ```python
    --8<-- "docs/examples/models/consistent_read.py"
    ```

=== "Sync (use sync_ prefix)"
    ```python
    --8<-- "docs/examples/models/sync_consistent_read.py"
    ```

**When to use strongly consistent reads:**

- You need to read data right after writing it
- Your app can't tolerate stale data (even for a second)
- You're building a financial or inventory system

**Trade-offs:**

| | Eventually consistent | Strongly consistent |
|---|---|---|
| Latency | Lower | Higher |
| Cost | 0.5 RCU per 4KB | 1 RCU per 4KB |
| Availability | Higher | Lower during outages |

Most apps work fine with eventually consistent reads. Use strongly consistent only when you need it.

### Update

There are two ways to update an item:

**Full update with save()**: Change attributes and call `save()`. This replaces the entire item:

```python
user = await User.get(pk="USER#123", sk="PROFILE")
user.name = "Jane"
user.age = 31
await user.save()

# Sync
user = User.sync_get(pk="USER#123", sk="PROFILE")
user.name = "Jane"
user.sync_save()
```

**Partial update with update()**: Update specific fields without touching others:

```python
user = await User.get(pk="USER#123", sk="PROFILE")
await user.update(name="Jane", age=31)

# Sync
user.sync_update(name="Jane", age=31)
```

The difference matters when you have many attributes. With `save()`, you send all attributes to DynamoDB. With `update()`, you only send the changed ones.

`update()` also updates the local object, so `user.name` is `"Jane"` after the call.

### Delete

To delete an item, call `delete()` on an instance:

```python
user = await User.get(pk="USER#123", sk="PROFILE")
await user.delete()

# Sync
user.sync_delete()
```

After deletion, the object still exists in Python, but the item is gone from DynamoDB.

### Update and delete by key

Sometimes you want to update or delete an item without fetching it first. The traditional approach requires two DynamoDB calls:

```python
user = await User.get(pk="USER#123", sk="PROFILE")  # Call 1
await user.update(name="Jane")                       # Call 2
```

Use `update_by_key()` and `delete_by_key()` to do it in one call:

=== "Async (default)"
    ```python
    --8<-- "docs/examples/models/key_operations.py"
    ```

=== "Sync (use sync_ prefix)"
    ```python
    --8<-- "docs/examples/models/sync_key_operations.py"
    ```

This is about 2x faster because you skip the read operation.

**When to use:**

- Bulk updates where you know the keys
- Background jobs that process many items
- Any case where you don't need the current item data

**Trade-offs:**

| Method | DynamoDB calls | Returns item? | Runs hooks? |
|--------|----------------|---------------|-------------|
| `get()` + `update()` | 2 | Yes | Yes |
| `update_by_key()` | 1 | No | No |
| `get()` + `delete()` | 2 | Yes | Yes |
| `delete_by_key()` | 1 | No | No |

!!! note
    These methods don't run lifecycle hooks. If you need hooks, use the traditional `get()` + `update()`/`delete()` approach.

## Advanced

### ModelConfig options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `table` | str | Required | DynamoDB table name |
| `client` | DynamoDBClient | None | Client to use (uses default if None) |
| `skip_hooks` | bool | False | Skip lifecycle hooks |
| `max_size` | int | None | Max item size in bytes |
| `consistent_read` | bool | False | Use strongly consistent reads by default |

### Setting a default client

Instead of passing a client to each model, set a default client once:

```python
from pydynox import DynamoDBClient, set_default_client

# At app startup
client = DynamoDBClient(region="us-east-1", profile="prod")
set_default_client(client)

# All models use this client
class User(Model):
    model_config = ModelConfig(table="users")
    pk = StringAttribute(hash_key=True)

class Order(Model):
    model_config = ModelConfig(table="orders")
    pk = StringAttribute(hash_key=True)
```

### Override client per model

Use a different client for specific models:

```python
# Default client for most models
set_default_client(prod_client)

# Special client for audit logs
audit_client = DynamoDBClient(region="eu-west-1")

class AuditLog(Model):
    model_config = ModelConfig(
        table="audit_logs",
        client=audit_client,  # Uses different client
    )
    pk = StringAttribute(hash_key=True)
```

### Converting to dict

```python
user = User(pk="USER#123", sk="PROFILE", name="John")
data = user.to_dict()
# {'pk': 'USER#123', 'sk': 'PROFILE', 'name': 'John'}
```

### Creating from dict

```python
data = {'pk': 'USER#123', 'sk': 'PROFILE', 'name': 'John'}
user = User.from_dict(data)
```

### Skipping hooks

If you have [lifecycle hooks](hooks.md) but want to skip them for a specific operation:

```python
user.save(skip_hooks=True)
user.delete(skip_hooks=True)
user.update(skip_hooks=True, name="Jane")
```

This is useful for:

- Data migrations where validation might fail on old data
- Bulk operations where you want maximum speed
- Fixing bad data that wouldn't pass validation

You can also disable hooks for all operations on a model:

```python
class User(Model):
    model_config = ModelConfig(table="users", skip_hooks=True)
```

!!! warning
    Be careful when skipping hooks. If you have validation in `before_save`, skipping it means invalid data can be saved to DynamoDB.

### Error handling

DynamoDB operations can fail for various reasons. Common errors:

| Exception | Cause |
|-----------|-------|
| `ResourceNotFoundException` | Table doesn't exist |
| `ProvisionedThroughputExceededException` | Exceeded capacity (throttled) |
| `ValidationException` | Invalid data (item too large, bad key, etc.) |
| `ConditionalCheckFailedException` | Conditional write failed |
| `ItemTooLargeException` | Item exceeds `max_size` (Python-only, before DynamoDB call) |

Wrap operations in try/except:

```python
from pydynox.exceptions import (
    ResourceNotFoundException,
    ProvisionedThroughputExceededException,
    PydynoxException,
)

try:
    await user.save()
except ResourceNotFoundException:
    print("Table doesn't exist")
except ProvisionedThroughputExceededException:
    print("Rate limited, try again")
except PydynoxException as e:
    print(f"DynamoDB error: {e}")
```

See [Exceptions](exceptions.md) for the full list.

## Testing your code

Test models without DynamoDB using the built-in memory backend:

=== "testing_models.py"
    ```python
    --8<-- "docs/examples/models/testing_models.py"
    ```

No setup needed. Just add `pydynox_memory_backend` to your test function. See [Testing](testing.md) for more details.

## Next steps

- [Query](query.md) - Query items by hash key with conditions
- [Attribute types](attributes.md) - All available attribute types
- [Indexes](indexes.md) - Query by non-key attributes with GSIs
- [Conditions](conditions.md) - Conditional writes
- [Hooks](hooks.md) - Lifecycle hooks for validation
