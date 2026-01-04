# ADR 004: Model and Client (high-level and low-level API)

## Status

Accepted

## Context

Users have different needs. Some want a simple ORM, others want full control.

## Decision

Provide two API levels:

1. **Model** - High-level ORM with typed attributes, hooks, and automatic serialization
2. **DynamoDBClient** - Low-level client that works with raw dicts

## Model (high-level)

```python
class User(Model):
    model_config = ModelConfig(table="users")
    pk = StringAttribute(hash_key=True)
    name = StringAttribute()

user = User(pk="USER#1", name="John")
user.save()
```

Benefits:
- Type safety
- IDE autocomplete
- Hooks (before_save, after_load, etc.)
- Automatic serialization
- Conditions with attribute references

## Client (low-level)

```python
client = DynamoDBClient()
client.put_item("users", {"pk": "USER#1", "name": "John"})
item = client.get_item("users", {"pk": "USER#1"})
```

Benefits:
- Full control
- No model overhead
- Works with any dict structure
- Good for migrations, scripts, one-off operations

## Why both?

- Model is great for application code
- Client is great for scripts, migrations, and edge cases
- Users can mix both in the same project
- Client is what Model uses internally

## Consequences

- Two ways to do things (could confuse beginners)
- More API surface to maintain
- Flexibility for different use cases
