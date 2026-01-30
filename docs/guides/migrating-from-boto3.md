# Migrating from boto3

boto3 is the official AWS SDK for Python. It's well-maintained, battle-tested, and works great for DynamoDB. pydynox is an alternative for teams who want an ORM-style experience with type safety and less boilerplate.

If boto3 works well for your use case, there's no need to migrate. This guide is for teams who want to try pydynox.

## Why consider pydynox?

| Feature | boto3 | pydynox |
|---------|-------|---------|
| Type safety | Manual | Built-in with IDE autocomplete |
| Serialization | Manual | Automatic |
| Update expressions | String-based | Pythonic |
| Compression | Manual | Built-in |
| Encryption | Manual | Built-in with KMS |
| Rate limiting | Manual | Built-in |
| Metrics | Manual | Built-in per operation |

## Same exceptions

pydynox uses the same exception names as boto3. This makes migration easier - your error handling code stays the same:

```python
# boto3
from botocore.exceptions import ClientError

try:
    table.put_item(...)
except ClientError as e:
    if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
        handle_condition_failed()

# pydynox - same exception name
from pydynox.exceptions import ConditionalCheckFailedException

try:
    user.save(condition=...)
except ConditionalCheckFailedException:
    handle_condition_failed()
```

All exceptions match boto3:

- `ConditionalCheckFailedException`
- `ResourceNotFoundException`
- `ResourceInUseException`
- `ValidationException`
- `ProvisionedThroughputExceededException`
- `TransactionCanceledException`
- `AccessDeniedException`

## Quick comparison

### Get item

=== "boto3"
    ```python
    --8<-- "docs/examples/migration/get_item_boto3.py"
    ```

=== "pydynox"
    ```python
    --8<-- "docs/examples/migration/get_item_pydynox.py"
    ```

### Put item

=== "boto3"
    ```python
    --8<-- "docs/examples/migration/put_item_boto3.py"
    ```

=== "pydynox"
    ```python
    --8<-- "docs/examples/migration/put_item_pydynox.py"
    ```

### Update item

=== "boto3"
    ```python
    --8<-- "docs/examples/migration/update_item_boto3.py"
    ```

=== "pydynox"
    ```python
    --8<-- "docs/examples/migration/update_item_pydynox.py"
    ```

### Query

=== "boto3"
    ```python
    --8<-- "docs/examples/migration/query_boto3.py"
    ```

=== "pydynox"
    ```python
    --8<-- "docs/examples/migration/query_pydynox.py"
    ```

### Conditional write

=== "boto3"
    ```python
    --8<-- "docs/examples/migration/conditional_boto3.py"
    ```

=== "pydynox"
    ```python
    --8<-- "docs/examples/migration/conditional_pydynox.py"
    ```

## Gradual migration

You don't need to rewrite everything at once:

1. Define Models for existing tables (keep using boto3)
2. Convert reads first (get, query) - they don't change data
3. Convert writes (put, update, delete)
4. Remove boto3 dependency when ready

## Working with both libraries

During migration, you can use both:

=== "interop.py"
    ```python
    --8<-- "docs/examples/migration/interop.py"
    ```

## Cheat sheet

pydynox has two APIs:

- **Model API** - ORM-style, type-safe, less boilerplate
- **Low-level API** - Similar to boto3, dict-based, full control

### Model API (recommended)

| Operation | boto3 | pydynox Model |
|-----------|-------|---------------|
| Get item | `table.get_item(Key={...})` | `Model.get(pk=..., sk=...)` |
| Put item | `table.put_item(Item={...})` | `model.save()` |
| Delete item | `table.delete_item(Key={...})` | `model.delete()` |
| Update item | `table.update_item(...)` | `model.update(name="new")` |
| Query | `table.query(...)` | `for item in Model.query(partition_key=...):` |
| Scan | `table.scan()` | `for item in Model.scan():` |
| Batch get | `dynamodb.batch_get_item(...)` | `Model.batch_get([keys])` |
| Conditional | `ConditionExpression=...` | `model.save(condition=Model.pk.not_exists())` |
| Projection | `ProjectionExpression=...` | `Model.get(..., fields=["name"])` |
| Consistent read | `ConsistentRead=True` | `Model.get(..., consistent_read=True)` |
| Create table | `client.create_table(...)` | `Model.create_table()` |
| Async | `aioboto3` | `await Model.async_get(...)` |

### Low-level API

For cases where you need full control or don't want to define models:

| Operation | boto3 | pydynox low-level |
|-----------|-------|-------------------|
| Get item | `table.get_item(Key={...})` | `client.get_item("table", {"pk": "123"})` |
| Put item | `table.put_item(Item={...})` | `client.put_item("table", {"pk": "123", ...})` |
| Delete item | `table.delete_item(Key={...})` | `client.delete_item("table", {"pk": "123"})` |
| Query | `table.query(...)` | `client.query("table", key_condition=...)` |
| Scan | `table.scan()` | `client.scan("table")` |
| Batch write | `table.batch_writer()` | `client.batch_write("table", put_items=[...])` |
| Transaction | `client.transact_write_items(...)` | `with Transaction(client) as txn:` |
| Create table | `client.create_table(...)` | `client.create_table("table", ...)` |
| Delete table | `client.delete_table(...)` | `client.delete_table("table")` |

## Extra features

pydynox adds some conveniences on top of DynamoDB:

- **Compression** - `compress=True` on attributes
- **Field encryption** - KMS encryption per field
- **Rate limiting** - Built-in throttling
- **Size calculator** - Check item size before save
- **Hooks** - `@before_save`, `@after_load` callbacks
- **Auto-generate** - Auto IDs with `UUIDGenerator()`
- **TTL helpers** - `expires_in()` methods
- **S3 for large items** - Store big data in S3 automatically
- **Metrics** - RCU/WCU tracking per operation
- **Optimistic locking** - `VersionAttribute`

## Next steps

- [Getting started](../getting-started.md) - Quick start guide
- [Models](models.md) - Define your data models
- [Query](query.md) - Query patterns
- [Conditions](conditions.md) - Conditional writes
