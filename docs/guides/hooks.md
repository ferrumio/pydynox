# Lifecycle hooks

Run code before or after model operations. Hooks let you add validation, logging, or any custom logic without cluttering your main code.

## Key features

- Validation before save
- Logging after operations
- Data transformation
- Side effects like sending emails

## Getting started

Hooks are methods decorated with special decorators. When you call `save()`, `delete()`, or `update()`, pydynox automatically runs the matching hooks.

### Available hooks

| Hook | When it runs |
|------|--------------|
| `@before_save` | Before `save()` |
| `@after_save` | After `save()` |
| `@before_delete` | Before `delete()` |
| `@after_delete` | After `delete()` |
| `@before_update` | Before `update()` |
| `@after_update` | After `update()` |
| `@after_load` | After `get()` or query |

### Basic usage

Here's a common pattern: validate and normalize data before saving, then log after:

=== "validation.py"
    ```python
    --8<-- "docs/examples/hooks/validation.py"
    ```

In this example:

1. `validate_email` runs first and raises an error if the email is invalid
2. `normalize` runs next and cleans up the data
3. The item is saved to DynamoDB
4. `log_save` runs last and prints a message

If any `before_*` hook raises an exception, the operation stops and the item is not saved.

## Advanced

### Multiple hooks of the same type

You can have multiple hooks of the same type. They run in the order they're defined in the class:

```python
class User(Model):
    @before_save
    def first_hook(self):
        print("This runs first")
    
    @before_save
    def second_hook(self):
        print("This runs second")
```

### All hooks example

Here's a model with all available hooks:

=== "all_hooks.py"
    ```python
    --8<-- "docs/examples/hooks/all_hooks.py"
    ```

### Skipping hooks

Sometimes you need to bypass hooks. For example, during data migration or when fixing bad data.

Skip hooks for a single operation:

```python
user.save(skip_hooks=True)
user.delete(skip_hooks=True)
user.update(skip_hooks=True, name="Jane")
```

Or disable hooks for all operations on a model:

```python
class User(Model):
    class Meta:
        table = "users"
        skip_hooks = True  # All hooks disabled by default
```

!!! warning
    Be careful when skipping hooks. If you have validation in `before_save`, skipping it means invalid data can be saved.

### Common patterns

| Pattern | Hook | Example |
|---------|------|---------|
| Validation | `@before_save` | Check email format, required fields |
| Normalization | `@before_save` | Lowercase email, trim whitespace |
| Timestamps | `@before_save` | Set `updated_at` field |
| Logging | `@after_save` | Log saved item ID |
| Audit | `@after_save` | Write to audit table |
| Cleanup | `@after_delete` | Delete related data, files |
| Transformation | `@after_load` | Format dates, compute fields |

### Hooks and transactions

Hooks run for each item in a transaction. If you're saving 10 items in a transaction, `before_save` runs 10 times.

If a hook raises an exception, the entire transaction fails and nothing is saved.


## Next steps

- [Auto-generate](auto-generate.md) - Generate IDs and timestamps
- [Models](models.md) - Model CRUD operations
- [Conditions](conditions.md) - Conditional writes
