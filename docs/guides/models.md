# Models

Models define the structure of your DynamoDB items.

## Key features

- Typed attributes with defaults
- Hash key and range key support
- Required fields with `null=False`
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

## Advanced

### ModelConfig options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `table` | str | Required | DynamoDB table name |
| `client` | DynamoDBClient | None | Client to use (uses default if None) |
| `skip_hooks` | bool | False | Skip lifecycle hooks |
| `max_size` | int | None | Max item size in bytes |

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

## Next steps

- [Attribute types](attributes.md) - All available attribute types
- [CRUD operations](crud.md) - Save, get, update, delete
- [Hooks](hooks.md) - Lifecycle hooks for validation
