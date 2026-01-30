# Table operations

Create, check, and delete DynamoDB tables programmatically.

pydynox is focused on runtime operations (CRUD, queries, batch). But table operations are useful for:

- Local development and testing
- CI/CD pipelines that set up test tables
- Scripts that bootstrap new environments
- Integration tests

For production, we recommend creating tables with IaC tools like CDK, Terraform, or CloudFormation. This avoids drift and keeps infrastructure separate from application code.

## Key features

- Create tables with hash key and optional range key
- Create tables from Model schema (auto-detects keys, GSIs, and LSIs)
- On-demand or provisioned billing
- Customer managed encryption (KMS)
- Wait for table to become active
- Check if table exists
- Async-first API (async by default, sync with `sync_` prefix)

## Async vs sync

Table operations follow the async-first pattern:

| Operation | Async (default) | Sync |
|-----------|-----------------|------|
| Create table | `await client.create_table(...)` | `client.sync_create_table(...)` |
| Check exists | `await client.table_exists(...)` | `client.sync_table_exists(...)` |
| Delete table | `await client.delete_table(...)` | `client.sync_delete_table(...)` |
| Wait for active | `await client.wait_for_table_active(...)` | `client.sync_wait_for_table_active(...)` |

Same pattern for Model:

| Operation | Async (default) | Sync |
|-----------|-----------------|------|
| Create table | `await User.create_table(...)` | `User.sync_create_table(...)` |
| Check exists | `await User.table_exists()` | `User.sync_table_exists()` |
| Delete table | `await User.delete_table()` | `User.sync_delete_table()` |

## Getting started

### Create a table from Model

The easiest way to create a table is from your Model. It uses the model's schema to build the table definition, including hash key, range key, and any GSIs.

=== "Async (default)"
    ```python
    --8<-- "docs/examples/tables/model_create_table_async.py"
    ```

=== "Sync"
    ```python
    --8<-- "docs/examples/tables/model_create_table.py"
    ```

This is the recommended approach because:

- No need to repeat key definitions
- GSIs are created automatically
- Attribute types are inferred from the model

### Create a table with client

You can also create tables directly with the client:

=== "Async (default)"
    ```python
    --8<-- "docs/examples/tables/create_table_async.py"
    ```

=== "Sync"
    ```python
    --8<-- "docs/examples/tables/create_table.py"
    ```

The `partition_key` and `sort_key` are tuples of `(attribute_name, attribute_type)`. Attribute types:

| Type | Description |
|------|-------------|
| `"S"` | String |
| `"N"` | Number |
| `"B"` | Binary |

### Check if table exists

Before creating a table, check if it already exists:

=== "Async (default)"
    ```python
    # Using Model
    if not await User.table_exists():
        await User.create_table(wait=True)

    # Using client
    client = DynamoDBClient()
    if not await client.table_exists("users"):
        await client.create_table("users", partition_key=("pk", "S"), wait=True)
    ```

=== "Sync"
    ```python
    # Using Model
    if not User.sync_table_exists():
        User.sync_create_table(wait=True)

    # Using client
    client = DynamoDBClient()
    if not client.sync_table_exists("users"):
        client.sync_create_table("users", partition_key=("pk", "S"), wait=True)
    ```

### Delete a table

=== "Async (default)"
    ```python
    # Using Model
    await User.delete_table()

    # Using client
    client = DynamoDBClient()
    await client.delete_table("users")
    ```

=== "Sync"
    ```python
    # Using Model
    User.sync_delete_table()

    # Using client
    client = DynamoDBClient()
    client.sync_delete_table("users")
    ```

!!! warning
    This permanently deletes the table and all its data. There is no confirmation prompt.

## Advanced

### Billing modes

DynamoDB offers two billing modes:

| Mode | Best for | Cost |
|------|----------|------|
| `PAY_PER_REQUEST` | Unpredictable traffic | Pay per read/write |
| `PROVISIONED` | Steady traffic | Fixed monthly cost |

On-demand (PAY_PER_REQUEST) is the default. For provisioned capacity:

=== "table_options.py"
    ```python
    --8<-- "docs/examples/tables/table_options.py"
    ```

With Model:

```python
User.create_table(
    billing_mode="PROVISIONED",
    read_capacity=10,
    write_capacity=5,
    wait=True,
)
```

### Table class

Choose a storage class based on access patterns:

| Class | Best for |
|-------|----------|
| `STANDARD` | Frequently accessed data (default) |
| `STANDARD_INFREQUENT_ACCESS` | Data accessed less than once per month |

Infrequent access costs less for storage but more for reads.

### Encryption

DynamoDB encrypts all data at rest. You can choose who manages the encryption key:

| Option | Description |
|--------|-------------|
| `AWS_OWNED` | AWS manages the key (default, free) |
| `AWS_MANAGED` | AWS KMS manages the key (costs extra) |
| `CUSTOMER_MANAGED` | You manage the key in KMS (full control) |

For `CUSTOMER_MANAGED`, you must provide the KMS key ARN.

### Wait for table

Tables take a few seconds to create. Use `wait=True` to block until the table is ready:

=== "Async (default)"
    ```python
    # Using Model
    await User.create_table(wait=True)
    # Table is now ready to use

    # Using client
    await client.create_table("users", partition_key=("pk", "S"), wait=True)
    ```

=== "Sync"
    ```python
    # Using Model
    User.sync_create_table(wait=True)
    # Table is now ready to use

    # Using client
    client.sync_create_table("users", partition_key=("pk", "S"), wait=True)
    ```

Or wait separately:

=== "Async (default)"
    ```python
    await client.create_table("users", partition_key=("pk", "S"))
    # Do other setup...
    await client.wait_for_table_active("users", timeout_seconds=30)
    ```

=== "Sync"
    ```python
    client.sync_create_table("users", partition_key=("pk", "S"))
    # Do other setup...
    client.sync_wait_for_table_active("users", timeout_seconds=30)
    ```

### Model table methods

| Method | Description |
|--------|-------------|
| `create_table(...)` | Create table (async) |
| `sync_create_table(...)` | Create table (sync) |
| `table_exists()` | Check if table exists (async) |
| `sync_table_exists()` | Check if table exists (sync) |
| `delete_table()` | Delete table (async) |
| `sync_delete_table()` | Delete table (sync) |

### Model.create_table() / Model.sync_create_table() parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `billing_mode` | str | `"PAY_PER_REQUEST"` | Billing mode |
| `read_capacity` | int | None | RCU (only for PROVISIONED) |
| `write_capacity` | int | None | WCU (only for PROVISIONED) |
| `table_class` | str | None | Storage class |
| `encryption` | str | None | Encryption type |
| `kms_key_id` | str | None | KMS key ARN |
| `wait` | bool | False | Wait for table to be active |

### Client table methods

| Method | Description |
|--------|-------------|
| `create_table(...)` | Create table (async) |
| `sync_create_table(...)` | Create table (sync) |
| `table_exists(table_name)` | Check if table exists (async) |
| `sync_table_exists(table_name)` | Check if table exists (sync) |
| `delete_table(table_name)` | Delete table (async) |
| `sync_delete_table(table_name)` | Delete table (sync) |
| `wait_for_table_active(table_name, ...)` | Wait for table (async) |
| `sync_wait_for_table_active(table_name, ...)` | Wait for table (sync) |

### client.create_table() / client.sync_create_table() parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `table_name` | str | Required | Name of the table |
| `partition_key` | tuple | Required | (name, type) for partition key |
| `sort_key` | tuple | None | (name, type) for sort key |
| `billing_mode` | str | `"PAY_PER_REQUEST"` | Billing mode |
| `read_capacity` | int | 5 | RCU (only for PROVISIONED) |
| `write_capacity` | int | 5 | WCU (only for PROVISIONED) |
| `table_class` | str | `"STANDARD"` | Storage class |
| `encryption` | str | `"AWS_OWNED"` | Encryption type |
| `kms_key_id` | str | None | KMS key ARN |
| `global_secondary_indexes` | list | None | GSI definitions |
| `wait` | bool | False | Wait for table to be active |


## Next steps

- [Indexes](indexes.md) - Add GSIs to your tables
- [IAM permissions](iam-permissions.md) - Required permissions for table operations
- [Models](models.md) - Define models for your tables
