# pydynox

A fast DynamoDB ORM for Python with a Rust core.

## Features

...
- Create and delete DynamoDB tables
- Wait for tables to become active
- **Wait for tables to be deleted** (NEW!)
- Sync and async APIs
- Vector Index support
- Full type hints

## Changes from v1.4.x

#### Added 

- `wait_for_table_deleted()` - wait for DynamoDB table to be fully deleted
- `delete_table(wait=True, timeout_seconds=None)` - delete with optional waiting  
- `sync_wait_for_table_deleted()` - sync version of `wait_for_table_deleted`

## Usage

### Async usage

```python
from pydynox import DynamoDBClient

async def example():
    client = DynamoDBClient(region="us-east-1")

    # Delete table and wait for deletion
    await client.delete_table("users", wait=True, timeout_seconds=60)
    
    # Or wait manually
    await client.delete_table("users")
    await client.wait_for_table_deleted("users", timeout_seconds=60)
```

### Sync usage

```python
from pydynox import DynamoDBClient

def example():
    client = DynamoDBClient(region="us-east-1")

    # Delete table and wait for deletion
    client.sync_delete_table("users", wait=True, timeout_seconds=60)
    
    # Or wait manually
    client.sync_delete_table("users")
    client.sync_wait_for_table_deleted("users", timeout_seconds=60)
```