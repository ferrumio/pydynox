# Field aliases

Use readable Python names while storing short names in DynamoDB.

## Why use aliases?

DynamoDB charges for storage. Attribute names are stored with every item. Long names add up fast.

Without aliases, you have two bad options:

1. Use short names in code (`em`, `fn`) - hard to read
2. Use long names in DynamoDB (`email`, `first_name`) - costs more

Aliases give you both: readable code and cheap storage.

## Key features

- Use `alias` parameter on any attribute
- Automatic translation on save and load
- Works with conditions, updates, queries, and scans
- Works with indexes (GSI and LSI)
- Zero performance cost - translation happens in Python at setup time

## Getting started

Add `alias` to any attribute. The alias is the name stored in DynamoDB.

=== "basic_alias.py"
    ```python
    --8<-- "docs/examples/alias/basic_alias.py"
    ```

The `alias` parameter is optional. Fields without it use the Python name as-is.

## CRUD operations

All CRUD operations work with Python names. The alias translation is automatic.

=== "alias_crud.py"
    ```python
    --8<-- "docs/examples/alias/alias_crud.py"
    ```

You never need to think about alias names in your code. Use Python names everywhere.

## Conditions and updates

Conditions and atomic updates also use aliases automatically.

=== "alias_conditions.py"
    ```python
    --8<-- "docs/examples/alias/alias_conditions.py"
    ```

When you write `Product.stock > 0`, pydynox translates `stock` to `stk` in the DynamoDB expression. You always use the Python name.

## Key aliases

You can alias key attributes too (partition key and sort key):

```python
class Event(Model):
    model_config = ModelConfig(table="events")

    pk = StringAttribute(partition_key=True, alias="p")
    sk = StringAttribute(sort_key=True, alias="s")
    event_type = StringAttribute(alias="et")
```

This saves bytes on every item since keys are always present.

!!! warning
    If you alias key attributes, the DynamoDB table must use the alias names as key definitions. When using `Model.create_table()`, this is handled automatically.

## Indexes

Aliases work with GSI and LSI definitions. The index key definitions use the alias name automatically.

```python
from pydynox.indexes import GlobalSecondaryIndex

class User(Model):
    model_config = ModelConfig(table="users")

    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
    email = StringAttribute(alias="em")

    email_index = GlobalSecondaryIndex(
        index_name="email-index",
        partition_key="email",  # Use Python name here
    )
```

When creating the table, the GSI key schema uses `em` (the alias). When querying, you use the Python name `email`.

## How it works

At class definition time, pydynox builds two lookup dicts:

- `_py_to_dynamo` - maps Python names to DynamoDB names (e.g., `{"email": "em"}`)
- `_dynamo_to_py` - maps DynamoDB names back to Python names (e.g., `{"em": "email"}`)

These dicts are used by:

- `to_dict()` - translates Python to DynamoDB (on save)
- `from_dict()` - translates DynamoDB to Python (on load)
- Conditions - uses alias in expression paths
- Atomic updates - uses alias in expression paths
- Projections - translates field names to aliases

Fields without an alias are not in these dicts. They use the Python name directly.

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `alias` | str \| None | None | DynamoDB attribute name. If set, this name is used in DynamoDB instead of the Python name. |

## Testing

Use `MemoryBackend` to test models with aliases. No DynamoDB needed.

=== "alias_testing.py"
    ```python
    --8<-- "docs/examples/alias/alias_testing.py"
    ```

## Tips

- Pick short but meaningful aliases: `em` for email, `fn` for first_name
- Be consistent: use the same alias pattern across models
- Document your aliases in a comment or table for your team
- Aliases are most useful for high-volume tables where storage costs matter

## Next steps

- [Attributes](attributes.md) - All attribute types and parameters
- [Conditions](conditions.md) - Filter and condition expressions
- [Indexes](indexes.md) - GSI and LSI with aliases
- [Size calculator](size-calculator.md) - See how much you save
