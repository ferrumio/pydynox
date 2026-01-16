# Atomic updates

Atomic updates modify values in DynamoDB without reading them first. This avoids race conditions when multiple requests update the same item.

## Key features

- Increment/decrement numbers without read-modify-write
- Append/prepend items to lists
- Set values only if attribute doesn't exist
- Remove attributes
- Combine multiple operations in one request
- Add conditions for safe updates

## The problem with read-modify-write

Without atomic updates, incrementing a counter looks like this:

```python
# Dangerous - race condition!
user = User.get(pk="USER#123")
user.login_count = user.login_count + 1
user.save()
```

If two requests run at the same time:

1. Request A reads `login_count = 5`
2. Request B reads `login_count = 5`
3. Request A writes `login_count = 6`
4. Request B writes `login_count = 6`

You lost an increment. The count should be 7, but it's 6.

Atomic updates solve this by doing the math in DynamoDB:

```python
# Safe - no race condition
user.update(atomic=[User.login_count.add(1)])
```

## Getting started

### Counters

The most common use case. Increment or decrement a number:

=== "counter.py"
    ```python
    --8<-- "docs/examples/atomic/counter.py"
    ```

Each `add(1)` is atomic. Even with thousands of concurrent requests, every increment is counted.

### Safe balance transfer

Combine atomic updates with conditions to prevent overdrafts:

=== "balance_transfer.py"
    ```python
    --8<-- "docs/examples/atomic/balance_transfer.py"
    ```

The condition `balance >= amount` is checked atomically with the update. If the balance is too low, the whole operation fails.

## Advanced

### Inventory management

Track stock and reservations atomically:

=== "inventory.py"
    ```python
    --8<-- "docs/examples/atomic/inventory.py"
    ```

Both `stock` and `reserved` are updated in one atomic operation. No item can be double-sold.

### Rate limiting

Enforce API rate limits with atomic counters:

=== "rate_limit_counter.py"
    ```python
    --8<-- "docs/examples/atomic/rate_limit_counter.py"
    ```

The condition ensures you can't exceed the limit, even with concurrent requests.

### Shopping cart

Manage cart items and totals:

=== "shopping_cart.py"
    ```python
    --8<-- "docs/examples/atomic/shopping_cart.py"
    ```

### List operations

Add items to lists without reading the whole list:

=== "user_tags.py"
    ```python
    --8<-- "docs/examples/atomic/user_tags.py"
    ```

### Default values

Set a value only if the attribute doesn't exist:

=== "if_not_exists.py"
    ```python
    --8<-- "docs/examples/atomic/if_not_exists.py"
    ```

### Multiple operations

Combine several atomic operations in one request:

=== "multiple_ops.py"
    ```python
    --8<-- "docs/examples/atomic/multiple_ops.py"
    ```

All operations happen atomically. Either all succeed or none do.

## Operations reference

| Method | Description | Example |
|--------|-------------|---------|
| `set(value)` | Set attribute to value | `User.name.set("Jane")` |
| `add(n)` | Add to number (use negative to subtract) | `User.count.add(1)` |
| `remove()` | Delete the attribute | `User.temp.remove()` |
| `append(items)` | Add items to end of list | `User.tags.append(["a", "b"])` |
| `prepend(items)` | Add items to start of list | `User.tags.prepend(["a"])` |
| `if_not_exists(value)` | Set only if attribute is missing | `User.count.if_not_exists(0)` |

## Error handling

When a condition fails, you get `ConditionalCheckFailedException`:

```python
from pydynox.exceptions import ConditionalCheckFailedException

try:
    account.update(
        atomic=[Account.balance.add(-100)],
        condition=Account.balance >= 100,
    )
except ConditionalCheckFailedException:
    print("Insufficient balance")
```

## When to use atomic updates

Use atomic updates when:

- Multiple requests might update the same item
- You need counters (views, likes, inventory)
- You want to avoid read-modify-write patterns
- You need guaranteed consistency

Use regular `update()` with kwargs when:

- You're the only writer
- You need to set values based on other fields
- You're doing a simple field update


## Testing your code

Test atomic updates without DynamoDB using the built-in memory backend:

=== "testing_atomic.py"
    ```python
    --8<-- "docs/examples/atomic/testing_atomic.py"
    ```

No setup needed. Just add `pydynox_memory_backend` to your test function. See [Testing](testing.md) for more details.

## Next steps

- [Observability](observability.md) - Track metrics on every operation
- [Conditions](conditions.md) - Add conditions to atomic updates
- [Transactions](transactions.md) - Combine atomic updates in transactions
