# Dataclass integration

Use Python dataclasses with DynamoDB. No extra dependencies needed - dataclasses are built into Python 3.7+.

## Key features

- Zero dependencies (dataclasses are built-in)
- Simple and lightweight
- Works with existing dataclasses
- All pydynox methods available

## Getting started

### Basic usage

Use the `@dynamodb_model` decorator on a dataclass:

=== "basic_dataclass.py"
    ```python
    --8<-- "docs/examples/integrations/basic_dataclass.py"
    ```

The decorator adds these methods to your dataclass:

- `save()` - Save to DynamoDB
- `get()` - Get by key
- `delete()` - Delete from DynamoDB
- `update()` - Update specific fields
- `_set_client()` - Set client after creation

Your dataclass works exactly as before - all dataclass features still work.

### With range key

Add a range key for composite keys:

```python
@dynamodb_model(table="users", partition_key="pk", sort_key="sk", client=client)
@dataclass
class User:
    pk: str
    sk: str
    name: str
```

### Setting client later

You can set the client after defining the model:

```python
@dynamodb_model(table="users", partition_key="pk")
@dataclass
class User:
    pk: str
    name: str

# Later, when you have the client
client = DynamoDBClient(region="us-east-1")
User._set_client(client)

# Now you can use it
user = User.get(pk="USER#1")
```

## Advanced

### Configuration options

| Option | Type | Description |
|--------|------|-------------|
| `table` | str | DynamoDB table name (required) |
| `partition_key` | str | Field name for partition key (required) |
| `sort_key` | str | Field name for sort key (optional) |
| `client` | DynamoDBClient | Client instance (optional, can set later) |

### Alternative: from_dataclass function

If you prefer not to use decorators:

```python
from dataclasses import dataclass
from pydynox.integrations.dataclass import from_dataclass

@dataclass
class User:
    pk: str
    sk: str
    name: str

UserDB = from_dataclass(User, table="users", partition_key="pk", sort_key="sk", client=client)
user = UserDB(pk="USER#1", sk="PROFILE", name="John")
user.save()
```

### Dataclass vs Pydantic

Choose dataclass when:

- You want zero dependencies
- You don't need validation
- Simple data structures are enough

Choose Pydantic when:

- You need validation
- You want type coercion
- You're already using Pydantic in your app

### Complex types

Dataclasses work with lists and dicts:

```python
@dynamodb_model(table="items", partition_key="pk", client=client)
@dataclass
class Item:
    pk: str
    tags: list
    metadata: dict

item = Item(
    pk="ITEM#1",
    tags=["tag1", "tag2"],
    metadata={"key": "value"}
)
item.save()
```

### Default values

Use dataclass defaults as usual:

```python
from dataclasses import dataclass, field

@dynamodb_model(table="users", partition_key="pk", client=client)
@dataclass
class User:
    pk: str
    name: str
    tags: list = field(default_factory=list)
    active: bool = True
```

!!! note
    The `@dynamodb_model` decorator must come before `@dataclass` in the decorator order.


## Next steps

- [Exceptions](exceptions.md) - Error handling
- [Models](models.md) - Native pydynox models
- [Pydantic](pydantic.md) - Use Pydantic for validation
