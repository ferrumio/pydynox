# Smart save

By default, pydynox tracks which fields changed and only sends those to DynamoDB.

## Why this matters

- Atomic partial updates (no race conditions from read-modify-write)
- Conditional updates (built-in support)
- Network bandwidth savings (sending less data over the wire)

Note that it doesn't save on WCUs as DynamoDB still charges based on the size of the item, not the size of attributes that were updated.

## How it works

When you load an item from DynamoDB, pydynox stores a snapshot of the original values. When you call `save()`, it compares current values with the original and only sends the changed fields using `UpdateItem`.

=== "basic.py"
    ```python
    --8<-- "docs/examples/smart_save/basic.py"
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
