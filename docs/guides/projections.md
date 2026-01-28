# Field projections

Fetch only the fields you need from DynamoDB.

## Why use field projections?

When you query or scan, DynamoDB returns all attributes by default. With projections, you tell DynamoDB which fields to return.

Benefits:

- Less data over the network
- Faster deserialization
- Smaller objects in memory

!!! note
    Projections reduce data transfer, not RCU cost. DynamoDB still reads the full item from disk. RCU is based on item size on disk, not what's returned.

## Key features

- Fetch specific fields from query and scan
- Works with Model API and Client API
- Supports nested attributes with dot notation
- Handles reserved words automatically

## Getting started

### Model API

Use the `fields` parameter on query and scan:

=== "basic_projection.py"
    ```python
    --8<-- "docs/examples/projections/basic_projection.py"
    ```

Works the same for scan:

=== "scan_projection.py"
    ```python
    --8<-- "docs/examples/projections/scan_projection.py"
    ```

### Client API

Use `projection` for get_item or `projection_expression` for query/scan:

=== "client_projection.py"
    ```python
    --8<-- "docs/examples/projections/client_projection.py"
    ```

## Advanced

### Nested attributes

Access nested fields with dot notation:

=== "nested_projection.py"
    ```python
    --8<-- "docs/examples/projections/nested_projection.py"
    ```

### Reserved words

Reserved words like `name` and `status` are handled automatically. The library creates placeholders for you:

```python
# "name" is a reserved word in DynamoDB
# This works without issues:
async for user in User.query(pk="USER#123", fields=["name", "status"]):
    print(user.name)
```

### Sync usage

Use `sync_query` and `sync_scan` for sync code:

```python
for user in User.sync_query(pk="USER#123", fields=["name"]):
    print(user.name)

for user in User.sync_scan(fields=["pk", "status"]):
    print(user.status)
```

## Parameters

### Model.query / Model.scan

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `fields` | list[str] | None | List of field names to fetch |

### client.get_item

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `projection` | list[str] | None | List of field names to fetch |

### client.query / client.scan

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `projection_expression` | str | None | DynamoDB projection expression |

## When to use

- Large items where you only need a few fields
- High-traffic queries where bandwidth matters
- Lambda functions where you want to minimize data transfer
- Reports or exports that need specific columns

!!! tip
    Projections are most useful when your items are large (>1KB) and you only need a few fields. For small items, the savings are minimal.

## Testing your code

Use the `pydynox_memory_backend` fixture to test projections without DynamoDB:

```python
import pytest
from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute


class User(Model):
    model_config = ModelConfig(table="users")
    pk = StringAttribute(hash_key=True)
    name = StringAttribute()
    email = StringAttribute()
    age = NumberAttribute()


@pytest.mark.asyncio
async def test_query_with_projection(pydynox_memory_backend):
    """Test query returns only projected fields."""
    await User(pk="USER#1", name="Alice", email="alice@example.com", age=30).save()
    await User(pk="USER#1", name="Bob", email="bob@example.com", age=25).save()

    results = [u async for u in User.query(hash_key="USER#1", fields=["name"])]

    assert len(results) == 2
    for user in results:
        assert user.name is not None
        # Non-projected fields are None
        assert user.email is None
        assert user.age is None


@pytest.mark.asyncio
async def test_scan_with_projection(pydynox_memory_backend):
    """Test scan returns only projected fields."""
    await User(pk="USER#1", name="Alice", email="alice@example.com", age=30).save()

    results = [u async for u in User.scan(fields=["pk", "name"])]

    assert len(results) == 1
    assert results[0].pk == "USER#1"
    assert results[0].name == "Alice"
    assert results[0].email is None
```

See the [Testing guide](testing.md) for more on `pydynox_memory_backend`.
