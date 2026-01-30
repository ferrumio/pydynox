# Pydantic integration

Use Pydantic models with DynamoDB. If you already have Pydantic models in your application, you can add DynamoDB persistence without rewriting them.

## Key features

- Use existing Pydantic models
- Automatic validation
- Type coercion
- All pydynox methods available

## Getting started

### Installation

Install pydynox with Pydantic support:

```bash
pip install pydynox[pydantic]
```

### Basic usage

Use the `@dynamodb_model` decorator on a Pydantic model:

=== "basic_pydantic.py"
    ```python
    --8<-- "docs/examples/integrations/basic_pydantic.py"
    ```

The decorator adds DynamoDB methods to your model. Async is the default:

| Async (default) | Sync |
|-----------------|------|
| `await model.save()` | `model.sync_save()` |
| `await model.delete()` | `model.sync_delete()` |
| `await model.update()` | `model.sync_update()` |
| `await Model.get()` | `Model.sync_get()` |

Plus `_set_client()` to set the client after creation.

Your Pydantic model works exactly as before - validation, serialization, and all other Pydantic features still work.

### With range key

Add a range key for composite keys:

```python
@dynamodb_model(table="users", partition_key="pk", sort_key="sk", client=client)
class User(BaseModel):
    pk: str
    sk: str
    name: str
```

### Pydantic validation

All Pydantic validation works. Invalid data raises `ValidationException` before anything is saved:

```python
from pydantic import BaseModel, EmailStr, Field

@dynamodb_model(table="users", partition_key="pk", client=client)
class User(BaseModel):
    pk: str
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    age: int = Field(ge=0, le=150)

# This raises ValidationException - email is invalid
user = User(pk="USER#1", name="", email="not-an-email", age=-1)
```

## Advanced

### Configuration options

| Option | Type | Description |
|--------|------|-------------|
| `table` | str | DynamoDB table name (required) |
| `partition_key` | str | Field name for partition key (required) |
| `sort_key` | str | Field name for sort key (optional) |
| `client` | DynamoDBClient | Client instance (optional, can set later) |

### Setting client later

You can set the client after defining the model:

```python
@dynamodb_model(table="users", partition_key="pk")
class User(BaseModel):
    pk: str
    name: str

# Later, when you have the client
client = DynamoDBClient(region="us-east-1")
User._set_client(client)

# Now you can use it
user = await User.get(pk="USER#1")
```

### Alternative: from_pydantic function

If you prefer not to use decorators:

```python
from pydynox.integrations.pydantic import from_pydantic

class User(BaseModel):
    pk: str
    sk: str
    name: str

UserDB = from_pydantic(User, table="users", partition_key="pk", sort_key="sk", client=client)
user = UserDB(pk="USER#1", sk="PROFILE", name="John")
await user.save()
```

### Why use Pydantic integration?

Benefits of using Pydantic with pydynox:

- **Validation** - Pydantic validates data before it reaches DynamoDB
- **Type coercion** - Strings become ints, etc.
- **IDE support** - Better autocomplete than raw dicts
- **Reuse models** - Use the same models for API and database
- **JSON Schema** - Auto-generated schemas for documentation

### Using Pydantic validators

Use Pydantic's `@field_validator` and `@model_validator` for validation:

```python
from pydantic import BaseModel, field_validator, model_validator

@dynamodb_model(table="users", partition_key="pk", client=client)
class User(BaseModel):
    pk: str
    email: str
    name: str
    
    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if "@" not in v:
            raise ValueError("Invalid email")
        return v.lower()  # Also normalize
    
    @model_validator(mode="before")
    @classmethod
    def set_defaults(cls, data: dict) -> dict:
        # Add computed fields, defaults, etc.
        return data
```

### Pydantic vs dataclass

Choose Pydantic when:

- You need validation
- You want type coercion
- You're already using Pydantic in your app

Choose dataclass when:

- You want zero dependencies
- You don't need validation
- Simple data structures are enough

### TTL with Pydantic

For TTL, use a datetime field:

```python
from datetime import datetime, timedelta, timezone

@dynamodb_model(table="sessions", partition_key="pk", client=client)
class Session(BaseModel):
    pk: str
    user_id: str
    expires_at: datetime
    
    @classmethod
    def create(cls, user_id: str, hours: int = 24) -> "Session":
        return cls(
            pk=f"SESSION#{uuid4()}",
            user_id=user_id,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=hours),
        )
    
    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) > self.expires_at
```

!!! note
    Remember to enable TTL on your DynamoDB table and set the attribute name to `expires_at`.


## Next steps

- [Dataclass](dataclass.md) - Use dataclasses with DynamoDB
- [Models](models.md) - Native pydynox models
- [Hooks](hooks.md) - Lifecycle hooks for validation
