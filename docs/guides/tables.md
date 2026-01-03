# Table operations

Create, check, and delete DynamoDB tables programmatically.

## Key features

- Create tables with hash key and optional range key
- On-demand or provisioned billing
- Customer managed encryption (KMS)
- Wait for table to become active
- Check if table exists

## Getting started

### Create a table

Use `create_table()` to create a new DynamoDB table:

=== "create_table.py"
    ```python
    --8<-- "docs/examples/tables/create_table.py"
    ```

The `hash_key` and `range_key` are tuples of `(attribute_name, attribute_type)`. Attribute types:

| Type | Description |
|------|-------------|
| `"S"` | String |
| `"N"` | Number |
| `"B"` | Binary |

### Check if table exists

Before creating a table, check if it already exists:

```python
client = DynamoDBClient()

if not client.table_exists("users"):
    client.create_table("users", hash_key=("pk", "S"), wait=True)
```

### Delete a table

```python
client = DynamoDBClient()
client.delete_table("users")
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

```python
client.create_table("users", hash_key=("pk", "S"), wait=True)
# Table is now ready to use
```

Or wait separately:

```python
client.create_table("users", hash_key=("pk", "S"))
# Do other setup...
client.wait_for_table_active("users", timeout_seconds=30)
```

### Create table parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `table_name` | str | Required | Name of the table |
| `hash_key` | tuple | Required | (name, type) for partition key |
| `range_key` | tuple | None | (name, type) for sort key |
| `billing_mode` | str | `"PAY_PER_REQUEST"` | Billing mode |
| `read_capacity` | int | 5 | RCU (only for PROVISIONED) |
| `write_capacity` | int | 5 | WCU (only for PROVISIONED) |
| `table_class` | str | `"STANDARD"` | Storage class |
| `encryption` | str | `"AWS_OWNED"` | Encryption type |
| `kms_key_id` | str | None | KMS key ARN |
| `wait` | bool | False | Wait for table to be active |


## Next steps

- [Indexes](indexes.md) - Add GSIs to your tables
- [IAM permissions](iam-permissions.md) - Required permissions for table operations
- [Models](models.md) - Define models for your tables
