# Conditions

Conditions let you add rules to `save()` and `delete()` operations. The operation only happens if the condition is true. If not, DynamoDB raises an error.

This is useful for:

- Preventing overwrites (only save if item doesn't exist)
- Optimistic locking (only update if version matches)
- Business rules (only withdraw if balance is sufficient)

## Key features

- Use Python operators (`==`, `>`, `<`) on model attributes
- Combine with `&` (AND), `|` (OR), `~` (NOT)
- Functions like `exists()`, `begins_with()`, `between()`
- Build conditions dynamically from user input

## Getting started

### Prevent overwriting existing items

The most common use case. Only save if the item doesn't exist yet:

=== "prevent_overwrite.py"
    ```python
    --8<-- "docs/examples/conditions/prevent_overwrite.py"
    ```

Without this condition, `save()` would silently overwrite any existing item with the same key. With the condition, you get a `ConditionCheckFailedError` if the item already exists.

### Safe delete

Only delete if certain conditions are met:

=== "safe_delete.py"
    ```python
    --8<-- "docs/examples/conditions/safe_delete.py"
    ```

This prevents accidental deletion of orders that are already being processed.

## Advanced

### Optimistic locking

When multiple processes might update the same item, use a version field to prevent lost updates:

=== "optimistic_lock.py"
    ```python
    --8<-- "docs/examples/conditions/optimistic_lock.py"
    ```

How it works:

1. Read the item and note the current version
2. Make your changes and increment the version
3. Save with a condition that the version still matches
4. If someone else updated it first, the condition fails

This is safer than "last write wins" because you know when conflicts happen.

### Complex business rules

Combine multiple conditions for complex validation:

=== "complex_rules.py"
    ```python
    --8<-- "docs/examples/conditions/complex_rules.py"
    ```

The withdrawal only happens if all three conditions are true. If any fails, the whole operation is rejected.

### Dynamic filters

Build conditions at runtime based on user input:

=== "dynamic_filters.py"
    ```python
    --8<-- "docs/examples/conditions/dynamic_filters.py"
    ```

Use `And()` and `Or()` from `pydynox.conditions` when you have a list of conditions to combine.

## Operators

### Comparison operators

| Operator | Example | Description |
|----------|---------|-------------|
| `==` | `User.status == "active"` | Equal |
| `!=` | `User.status != "deleted"` | Not equal |
| `>` | `User.age > 18` | Greater than |
| `>=` | `User.age >= 21` | Greater or equal |
| `<` | `User.age < 65` | Less than |
| `<=` | `User.age <= 30` | Less or equal |

### Combining operators

| Operator | Example | Description |
|----------|---------|-------------|
| `&` | `(a > 1) & (b < 2)` | Both must be true |
| `\|` | `(a == 1) \| (a == 2)` | Either can be true |
| `~` | `~a.exists()` | Negates the condition |

!!! warning
    Always use parentheses when combining conditions. Python's operator precedence may not work as expected.

### Function conditions

| Function | Example | Description |
|----------|---------|-------------|
| `exists()` | `User.email.exists()` | Attribute exists |
| `does_not_exist()` | `User.pk.does_not_exist()` | Attribute doesn't exist |
| `begins_with()` | `User.sk.begins_with("ORDER#")` | String starts with prefix |
| `contains()` | `User.tags.contains("vip")` | List contains value |
| `between()` | `User.age.between(18, 65)` | Value in range (inclusive) |
| `is_in()` | `User.status.is_in("a", "b")` | Value in list |

### Nested attributes

Access nested map keys and list indexes:

```python
# Map access
User.address["city"] == "NYC"

# List access
User.tags[0] == "premium"

# Deep nesting
User.metadata["preferences"]["theme"] == "dark"
```

## Error handling

When a condition fails, DynamoDB raises `ConditionCheckFailedError`:

```python
from pydynox.exceptions import ConditionCheckFailedError

try:
    user.save(condition=User.pk.does_not_exist())
except ConditionCheckFailedError:
    print("User already exists")
```

## Type hints

Use `Condition` for type hints:

```python
from pydynox import Condition

def apply_filter(cond: Condition) -> None:
    ...
```
