# Optimistic locking

Optimistic locking prevents concurrent updates from overwriting each other. When two processes try to update the same item, the second one fails instead of silently overwriting the first.

## How it works

Add a `VersionAttribute` to your model. pydynox handles the rest:

1. First save sets version to 1
2. Each save increments version by 1
3. Before saving, pydynox checks that the version in DynamoDB matches the local version
4. If versions don't match, save fails with `ConditionalCheckFailedException`

## Basic usage

=== "basic_version.py"
    ```python
    --8<-- "docs/examples/optimistic_locking/basic_version.py"
    ```

## Concurrent updates

When two processes load the same item and try to update it:

=== "concurrent_update.py"
    ```python
    --8<-- "docs/examples/optimistic_locking/concurrent_update.py"
    ```

## Handling conflicts

When a save fails due to version mismatch, reload the item and retry:

=== "handle_conflict.py"
    ```python
    --8<-- "docs/examples/optimistic_locking/handle_conflict.py"
    ```

### Get the current item without extra GET

Use `return_values_on_condition_check_failure=True` to get the current item directly from the exception. This saves a round trip:

```python
from pydynox.pydynox_core import ConditionalCheckFailedException

try:
    client.update_item(
        "users",
        {"pk": "USER#123"},
        updates={"name": "Alice", "version": 2},
        condition_expression="#v = :expected",
        expression_attribute_names={"#v": "version"},
        expression_attribute_values={":expected": 1},
        return_values_on_condition_check_failure=True,
    )
except ConditionalCheckFailedException as e:
    # No extra GET needed
    current_version = e.item["version"]
    print(f"Version conflict! Current version is {current_version}")
```

## Async with high concurrency

For async code with many concurrent operations, always use retry with backoff:

=== "async_version.py"
    ```python
    --8<-- "docs/examples/optimistic_locking/async_version.py"
    ```

## Delete with version check

Delete also checks the version. If someone else updated the item, delete fails:

=== "delete_version.py"
    ```python
    --8<-- "docs/examples/optimistic_locking/delete_version.py"
    ```

## Combining with user conditions

You can add your own conditions. They're combined with the version check using AND:

=== "user_condition.py"
    ```python
    --8<-- "docs/examples/optimistic_locking/user_condition.py"
    ```

## When to use

| Use case | Examples | Recommendation |
|----------|----------|----------------|
| Counters and balances | Page views, account balances, inventory | ✅ Use it |
| Documents with edits | Wiki pages, configs, user profiles | ✅ Use it |
| State machines | Order status, workflow steps | ✅ Use it |
| Shared resources | Seat reservations, appointment slots | ✅ Use it |
| High-frequency updates | Hot keys, real-time counters | ❌ Use transactions |
| Simple increments | Like counts, view counts | ❌ Use `update()` with `add()` |
| Single writer per item | Background jobs, migrations | ❌ Skip it |

## Things to know

**Version increments before save.** If save fails, your local object has a wrong version. Always reload after a failed save.

**`update()` does not use versioning.** Only `save()` and `delete()` check and increment the version. If you need atomic field updates with versioning, reload and save.

**New items check for existence.** Creating an item with `VersionAttribute` uses `attribute_not_exists` condition. Creating the same item twice fails.

**Use retry with backoff.** In high-concurrency scenarios, add exponential backoff between retries to reduce contention.
