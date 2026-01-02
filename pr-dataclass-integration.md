# feat: add dataclass integration

## Summary

Added support for Python dataclasses. Use `@dynamodb_model` on any dataclass to get DynamoDB persistence.

## Usage

```python
from dataclasses import dataclass
from pydynox import DynamoDBClient, dynamodb_model

client = DynamoDBClient(region="us-east-1")

@dynamodb_model(table="users", hash_key="pk", range_key="sk", client=client)
@dataclass
class User:
    pk: str
    sk: str
    name: str
    age: int = 0

# Save
user = User(pk="USER#1", sk="PROFILE", name="John", age=30)
user.save()

# Get
user = User.get(pk="USER#1", sk="PROFILE")

# Update
user.update(name="Jane")

# Delete
user.delete()
```

## Changes

- `integrations/dataclass.py` - dataclass support
- `integrations/functions.py` - unified decorator that detects dataclass vs Pydantic
- `integrations/_base.py` - shared code
- `docs/guides/dataclass.md` - documentation
- Exported `dynamodb_model` from main `__init__.py`

## Tests

- 17 unit tests
- 5 integration tests

All passing.

## Why?

- Zero dependencies (dataclasses are built into Python 3.7+)
- Some users don't need Pydantic validation
- Simpler for basic use cases

Closes #68
