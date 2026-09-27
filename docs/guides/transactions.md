# Transactions

Run multiple operations that succeed or fail together. If any operation fails, DynamoDB rolls back all changes automatically.

## Key features

- All-or-nothing operations
- Put, delete, update, and condition checks in a write transaction
- Atomic reads through `transact_get`
- Max 100 items per transaction
- Optional request tokens for idempotent writes

## Getting started

Transactions are useful when you need to update related data atomically. For example, when creating an order, you might want to:

1. Create the order record
2. Update the user's order count
3. Decrease inventory

If any of these fails, you don't want partial data. Transactions guarantee all operations succeed or none do.

=== "transaction.py"
    ```python
    --8<-- "docs/examples/transactions/transaction.py"
    ```

When you use `Transaction` as a context manager, it automatically commits when the block ends. If an exception occurs inside the block, the transaction is not committed.

## Reading multiple items

Use `transact_get` to read multiple items atomically. This gives you a consistent snapshot - all items are read at the same point in time.

=== "transact_get.py"
    ```python
    --8<-- "docs/examples/transactions/transact_get.py"
    ```

This is useful when you need to read related data that must be consistent. For example, reading a user and their orders together.

## Writing with client methods

You can also use `transact_write` directly for more complex operations:

=== "transact_write.py"
    ```python
    --8<-- "docs/examples/transactions/transact_write.py"
    ```

## Retrying a transaction with a request token

A write can succeed in DynamoDB even if your application receives a timeout. Retrying it in a new call could apply the same change twice, such as reserving stock twice.

Pass `client_request_token` to identify retries of the same transaction. DynamoDB applies identical requests with the same token only once within its idempotency window.

=== "Async (default)"
    ```python
    --8<-- "docs/examples/transactions/idempotency.py"
    ```

=== "Sync"
    ```python
    --8<-- "docs/examples/transactions/sync_idempotency.py"
    ```

Both client methods also accept the token:

```python
await client.transact_write(operations, client_request_token=token)
client.sync_transact_write(operations, client_request_token=token)
```

The parameter is optional and keyword-only. Existing calls keep their current behavior. Omitting it or passing `None` lets the AWS SDK generate a token for each call; that generated token is reused by the SDK's own retries.

### Token rules

- Use a string of 1–36 characters. Invalid lengths raise `ValueError` before a request is sent.
- Create or store the token once for each logical operation. Reuse it across application retries or process restarts.
- The token is valid for ten minutes after the first request completes. After that, DynamoDB treats the same token as a new request.
- Retry with the same request parameters, including IDs, timestamps, conditions, and version values. Changing them while reusing the token raises `IdempotentParameterMismatchException`, available from `pydynox.exceptions`.
- Use a new token for a new logical operation.

If `commit()` raises a connection error, the transaction keeps its queued operations. You can retry `commit()` on that object without rebuilding the payload. A successful commit clears the queue. Rebuilding a transaction with `save_model()` may generate new IDs, timestamps, or version values, so it is not necessarily the same request.

This token covers DynamoDB transaction writes. It does not deduplicate Python hooks, external side effects, or requests beyond the ten-minute window.

See [AWS ClientRequestToken](https://docs.aws.amazon.com/amazondynamodb/latest/APIReference/API_TransactWriteItems.html#DDB-TransactWriteItems-request-ClientRequestToken) for the service behavior.

## API reference

### Transaction class

| Method | Description |
|--------|-------------|
| `tx.put(table, item)` | Add or replace an item |
| `tx.delete(table, key)` | Remove an item |
| `tx.update(table, key, updates)` | Update specific attributes |
| `tx.condition_check(table, key, condition)` | Check a condition without modifying |

Both `Transaction(client, *, client_request_token=None)` and `SyncTransaction(client, *, client_request_token=None)` accept an optional token.

### Client methods

| Async (default) | Sync | Description |
|-----------------|------|-------------|
| `await client.transact_write(ops)` | `client.sync_transact_write(ops)` | Write multiple items atomically |
| `await client.transact_get(gets)` | `client.sync_transact_get(gets)` | Read multiple items atomically |

### Classes

| Async (default) | Sync | Description |
|-----------------|------|-------------|
| `Transaction` | `SyncTransaction` | Context manager for transactions |

## Limits

DynamoDB transactions have limits you should know:

| Limit | Value |
|-------|-------|
| Max items | 100 |
| Max size | 4 MB total |
| Region | All items must be in the same region |

If you exceed these limits, the transaction fails before any operation runs.

## When to use transactions

**Use transactions when:**

- You need all-or-nothing behavior
- You're updating related data that must stay consistent
- You need to check conditions before writing (like "only update if version matches")
- You need a consistent snapshot of multiple items

**Don't use transactions for:**

- Simple single-item operations (just use `save()`)
- High-throughput batch writes (use `BatchWriter` instead - it's faster)
- Operations that can tolerate partial success

!!! tip
    Transactions cost twice as much as regular operations because DynamoDB does extra work to guarantee atomicity. Use them only when you need the guarantee.

## Error handling

If DynamoDB cancels a transaction, none of its writes are applied. A connection error or timeout can leave the outcome unknown; use the same request token when retrying, as described above.

=== "error_handling.py"
    ```python
    --8<-- "docs/examples/transactions/error_handling.py"
    ```

Common reasons for transaction failures:

- Item size exceeds 400 KB
- Total transaction size exceeds 4 MB
- More than 100 items
- Condition check failed
- Throughput exceeded
- Reusing a request token with different parameters

## Sync API

For sync code, use `SyncTransaction` and the `sync_` prefixed methods:

=== "sync_transaction.py"
    ```python
    --8<-- "docs/examples/transactions/sync_transaction.py"
    ```

## Next steps

- [Tables](tables.md) - Create and manage tables
- [Conditions](conditions.md) - Add conditions to transactions
- [Exceptions](exceptions.md) - Handle transaction errors
