# Transactions

Run multiple operations that succeed or fail together. If any operation fails, DynamoDB rolls back all changes automatically.

## Key features

- All-or-nothing operations
- Put, delete, and update in one transaction
- Max 100 items per transaction
- Metrics on every operation (see [observability](observability.md))

## Getting started

Transactions are useful when you need to update related data atomically. For example, when creating an order, you might want to:

1. Create the order record
2. Update the user's order count
3. Decrease inventory

If any of these fails, you don't want partial data. Transactions guarantee all operations succeed or none do.

=== "basic_transaction.py"
    ```python
    --8<-- "docs/examples/transactions/basic_transaction.py"
    ```

When you use `Transaction` as a context manager, it automatically commits when the block ends. If an exception occurs inside the block, the transaction is not committed.

## Advanced

### Transaction operations

You can mix different operations in one transaction:

| Operation | Description |
|-----------|-------------|
| `tx.put(table, item)` | Add or replace an item |
| `tx.delete(table, key)` | Remove an item |
| `tx.update(table, key, updates)` | Update specific attributes |

```python
with Transaction(client) as tx:
    # Create new item
    tx.put("users", {"pk": "USER#1", "name": "John"})
    
    # Update existing item
    tx.update("users", {"pk": "USER#2"}, {"order_count": 5})
    
    # Delete item
    tx.delete("temp", {"pk": "TEMP#1"})
```

### Limits

DynamoDB transactions have limits you should know:

| Limit | Value |
|-------|-------|
| Max items | 100 |
| Max size | 4 MB total |
| Region | All items must be in the same region |

If you exceed these limits, the transaction fails before any operation runs.

### When to use transactions

**Use transactions when:**

- You need all-or-nothing behavior
- You're updating related data that must stay consistent
- You need to check conditions before writing (like "only update if version matches")

**Don't use transactions for:**

- Simple single-item operations (just use `save()`)
- High-throughput batch writes (use `BatchWriter` instead - it's faster)
- Operations that can tolerate partial success

!!! tip
    Transactions cost twice as much as regular operations because DynamoDB does extra work to guarantee atomicity. Use them only when you need the guarantee.

### Error handling

If a transaction fails, DynamoDB returns an error and no changes are made:

```python
try:
    with Transaction(client) as tx:
        tx.put("users", {"pk": "USER#1", "name": "John"})
        tx.put("orders", {"pk": "ORDER#1", "user": "USER#1"})
except Exception as e:
    print(f"Transaction failed: {e}")
    # No changes were made to either table
```

Common reasons for transaction failures:

- Item size exceeds 400 KB
- Total transaction size exceeds 4 MB
- More than 100 items
- Condition check failed
- Throughput exceeded


## Next steps

- [Tables](tables.md) - Create and manage tables
- [Conditions](conditions.md) - Add conditions to transactions
- [Exceptions](exceptions.md) - Handle transaction errors
