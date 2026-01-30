# Smart save

By default, pydynox tracks which fields changed and only sends those to DynamoDB. This saves WCU (Write Capacity Units) when updating large items.

## Why this matters

DynamoDB charges for every byte you write. If you have a 10KB item and change one field, sending all 10KB wastes 9 WCU.

pydynox optimizes this. It only sends the changed field. One field = 1 WCU instead of 10.

This adds up fast:

- 1 million updates/month on 4KB items
- Without smart save: 4M WCU = $50/month
- With smart save (200B average change): 200K WCU = $2.50/month
- Savings: $47.50/month

## How it works

When you load an item from DynamoDB, pydynox stores a snapshot of the original values. When you call `save()`, it compares current values with the original and only sends the changed fields using `UpdateItem`.

=== "basic.py"
    ```python
    --8<-- "docs/examples/smart_save/basic.py"
    ```

## Cost savings

DynamoDB charges 1 WCU per 1KB written.

| Item size | Fields changed | Without smart save | With smart save | Savings |
|-----------|----------------|-------------------|-----------------|---------|
| 1KB | 1 field (50B) | 1 WCU | 1 WCU | 0% |
| 4KB | 1 field (50B) | 4 WCU | 1 WCU | 75% |
| 10KB | 1 field (50B) | 10 WCU | 1 WCU | 90% |
| 4KB | 2KB of fields | 4 WCU | 2 WCU | 50% |

## Measure WCU consumed

Run this example to see the WCU difference between smart save and full replace:

=== "wcu_comparison.py"
    ```python
    --8<-- "docs/examples/smart_save/wcu_comparison.py"
    ```

Example output:

```
=== WCU Comparison ===
Smart save (UpdateItem): 1 WCU
Full replace (PutItem):  2 WCU
Savings: 1 WCU
```

## Check if item changed

Use `is_dirty` and `changed_fields` to see what changed:

=== "check_changes.py"
    ```python
    --8<-- "docs/examples/smart_save/check_changes.py"
    ```

## Force full replace

If you need to replace the entire item (using `PutItem` instead of `UpdateItem`), use `full_replace=True`:

=== "full_replace.py"
    ```python
    --8<-- "docs/examples/smart_save/full_replace.py"
    ```

Use this when:

- You want to remove fields that are not in the model
- You need `PutItem` behavior for some reason

## New items

New items (not loaded from DynamoDB) always use `PutItem`:

=== "new_items.py"
    ```python
    --8<-- "docs/examples/smart_save/new_items.py"
    ```

## With conditions

Smart save works with conditions:

=== "with_condition.py"
    ```python
    --8<-- "docs/examples/smart_save/with_condition.py"
    ```

## With optimistic locking

Smart save works with version attributes:

=== "with_version.py"
    ```python
    --8<-- "docs/examples/smart_save/with_version.py"
    ```
