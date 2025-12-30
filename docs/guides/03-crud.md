# CRUD operations

Basic create, read, update, delete operations. These are the most common operations you'll do with DynamoDB.

## Key features

- `save()` to create or replace items
- `get()` to read by key
- `update()` for partial updates
- `delete()` to remove items

## Getting started

Here's a complete example showing all CRUD operations:

=== "crud_operations.py"
    ```python
    --8<-- "docs/examples/models/crud_operations.py"
    ```

Let's break down each operation.

### Create

To create a new item, instantiate your model and call `save()`:

```python
user = User(pk="USER#123", sk="PROFILE", name="John", age=30)
user.save()
```

If an item with the same key already exists, `save()` replaces it completely. This is how DynamoDB works - there's no separate "create" vs "update" at the API level.

### Read

To get an item by its key, use the class method `get()`:

```python
user = User.get(pk="USER#123", sk="PROFILE")
if user:
    print(user.name)
else:
    print("User not found")
```

`get()` returns `None` if the item doesn't exist. Always check for `None` before using the result.

If your table has only a hash key (no range key), you only need to pass the hash key:

```python
user = User.get(pk="USER#123")
```

### Update

There are two ways to update an item:

**Full update with save()**: Change attributes and call `save()`. This replaces the entire item:

```python
user = User.get(pk="USER#123", sk="PROFILE")
user.name = "Jane"
user.age = 31
user.save()
```

**Partial update with update()**: Update specific fields without touching others:

```python
user = User.get(pk="USER#123", sk="PROFILE")
user.update(name="Jane", age=31)
```

The difference matters when you have many attributes. With `save()`, you send all attributes to DynamoDB. With `update()`, you only send the changed ones.

`update()` also updates the local object, so `user.name` is `"Jane"` after the call.

### Delete

To delete an item, call `delete()` on an instance:

```python
user = User.get(pk="USER#123", sk="PROFILE")
user.delete()
```

After deletion, the object still exists in Python, but the item is gone from DynamoDB.

## Advanced

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
    class Meta:
        table = "users"
        skip_hooks = True  # All hooks disabled by default
```

!!! warning
    Be careful when skipping hooks. If you have validation in `before_save`, skipping it means invalid data can be saved to DynamoDB.

### Error handling

DynamoDB operations can fail for various reasons. Common errors:

| Error | Cause |
|-------|-------|
| `ResourceNotFoundException` | Table doesn't exist |
| `ProvisionedThroughputExceededException` | Exceeded capacity |
| `ValidationException` | Invalid data (item too large, etc.) |

Wrap operations in try/except if you need to handle errors:

```python
try:
    user.save()
except Exception as e:
    print(f"Failed to save: {e}")
```

### Conditional operations

DynamoDB supports conditional writes - only save if a condition is met. This is useful for optimistic locking and preventing overwrites.

!!! note
    Conditional operations are planned but not yet implemented in pydynox.
