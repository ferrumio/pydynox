# pydynox 🐍⚙️

[![CI](https://github.com/leandrodamascena/pydynox/actions/workflows/ci.yml/badge.svg)](https://github.com/leandrodamascena/pydynox/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/pydynox.svg)](https://pypi.org/project/pydynox/)
[![Python versions](https://img.shields.io/pypi/pyversions/pydynox.svg)](https://pypi.org/project/pydynox/)
[![License](https://img.shields.io/pypi/l/pydynox.svg)](https://github.com/leandrodamascena/pydynox/blob/main/LICENSE)
[![Downloads](https://static.pepy.tech/badge/pydynox/month)](https://pepy.tech/project/pydynox)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/leandrodamascena/pydynox/badge)](https://securityscorecards.dev/viewer/?uri=github.com/leandrodamascena/pydynox)

A fast DynamoDB ORM for Python with a Rust core.

> 📢 **Stable Release: March 2-6, 2026** - We're in the final stretch! The API is stabilizing, performance is being polished, and we're building the remaining features. We might release earlier if everything goes well. Stay tuned!

## Why "pydynox"?

**Py**(thon) + **Dyn**(amoDB) + **Ox**(ide/Rust)

## GenAI Contributions 🤖

I believe GenAI is transforming how we build software. It's a powerful tool that accelerates development when used by developers who understand what they're doing.

To support both humans and AI agents, I created:

- `.ai/` folder - Guidelines for agentic IDEs (Cursor, Windsurf, Kiro, etc.)
- `ADR/` folder - Architecture Decision Records for humans to understand the "why" behind decisions

**If you're contributing with AI help:**

- Understand what the AI generated before submitting
- Make sure the code follows the project patterns
- Test your changes

I reserve the right to reject low-quality PRs where project patterns are not followed and it's clear that GenAI was driving instead of the developer.

## Features

- Simple class-based API like PynamoDB
- Fast serialization with Rust
- Batch operations with auto-splitting
- Transactions
- Global Secondary Indexes
- Async support
- Pydantic integration
- TTL (auto-expiring items)
- Lifecycle hooks
- Auto-generate IDs and timestamps
- Optimistic locking
- Rate limiting
- Field encryption (KMS)
- Compression (zstd, lz4, gzip)
- S3 attribute for large files
- PartiQL support
- Observability (logging, metrics, OpenTelemetry tracing)

## Installation

```bash
pip install pydynox
```

For Pydantic support:

```bash
pip install pydynox[pydantic]
```

For OpenTelemetry tracing:

```bash
pip install pydynox[opentelemetry]
```

## Quick Start

### Define a Model

```python
from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute, NumberAttribute, BooleanAttribute, ListAttribute

class User(Model):
    model_config = ModelConfig(table="users")
    
    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    name = StringAttribute()
    email = StringAttribute()
    age = NumberAttribute(default=0)
    active = BooleanAttribute(default=True)
    tags = ListAttribute()
```

### CRUD Operations

```python
# Create
user = User(pk="USER#123", sk="PROFILE", name="John", email="john@test.com")
user.save()

# Read
user = User.get(pk="USER#123", sk="PROFILE")

# Update - full save
user.name = "John Doe"
user.save()

# Update - partial
user.update(name="John Doe", age=31)

# Delete
user.delete()
```

### Query

```python
# Query by hash key
for user in User.query(hash_key="USER#123"):
    print(user.name)

# With range key condition
for user in User.query(
    hash_key="USER#123",
    range_key_condition=User.sk.begins_with("ORDER#")
):
    print(user.sk)

# With filter
for user in User.query(
    hash_key="USER#123",
    filter_condition=User.age > 18
):
    print(user.name)

# Get first result
first = User.query(hash_key="USER#123").first()

# Collect all
users = list(User.query(hash_key="USER#123"))
```

### Conditions

Conditions use attribute operators directly:

```python
# Save only if item doesn't exist
user.save(condition=User.pk.not_exists())

# Delete with condition
user.delete(condition=User.version == 5)

# Combine conditions with & (AND) and | (OR)
user.save(
    condition=User.pk.not_exists() | (User.version == 1)
)
```

Available condition methods:
- `User.field == value` - equals
- `User.field != value` - not equals
- `User.field > value` - greater than
- `User.field >= value` - greater than or equal
- `User.field < value` - less than
- `User.field <= value` - less than or equal
- `User.field.exists()` - attribute exists
- `User.field.not_exists()` - attribute does not exist
- `User.field.begins_with(prefix)` - string starts with
- `User.field.contains(value)` - string or list contains
- `User.field.between(low, high)` - value in range
- `User.field.is_in(val1, val2, ...)` - value in list

### Atomic Updates

```python
# Increment a number
user.update(atomic=[User.age.add(1)])

# Append to list
user.update(atomic=[User.tags.append(["verified"])])

# Remove from list
user.update(atomic=[User.tags.remove([0])])  # Remove first element

# Set if not exists
user.update(atomic=[User.views.if_not_exists(0)])

# Multiple atomic operations
user.update(atomic=[
    User.age.add(1),
    User.tags.append(["premium"]),
])

# With condition
user.update(
    atomic=[User.age.add(1)],
    condition=User.status == "active"
)
```

### Batch Operations

```python
from pydynox import BatchWriter, DynamoDBClient

client = DynamoDBClient()

# Batch write - items are sent in groups of 25
with BatchWriter(client, "users") as batch:
    for i in range(100):
        batch.put({"pk": f"USER#{i}", "sk": "PROFILE", "name": f"User {i}"})

# Mix puts and deletes
with BatchWriter(client, "users") as batch:
    batch.put({"pk": "USER#1", "sk": "PROFILE", "name": "John"})
    batch.delete({"pk": "USER#2", "sk": "PROFILE"})
```

### Global Secondary Index

```python
from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute
from pydynox.indexes import GlobalSecondaryIndex

class User(Model):
    model_config = ModelConfig(table="users")
    
    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    email = StringAttribute()
    status = StringAttribute()
    
    # GSI with hash key only
    email_index = GlobalSecondaryIndex(
        index_name="email-index",
        hash_key="email",
    )
    
    # GSI with hash and range key
    status_index = GlobalSecondaryIndex(
        index_name="status-index",
        hash_key="status",
        range_key="pk",
    )

# Query on index
for user in User.email_index.query(hash_key="john@test.com"):
    print(user.name)
```

### Transactions

```python
import asyncio
from pydynox import DynamoDBClient, Transaction

client = DynamoDBClient()

async def create_order():
    async with Transaction(client) as tx:
        tx.put("users", {"pk": "USER#1", "sk": "PROFILE", "name": "John"})
        tx.put("orders", {"pk": "ORDER#1", "sk": "DETAILS", "user": "USER#1"})

asyncio.run(create_order())
```

### Async support

```python
# All methods have async versions with async_ prefix
user = await User.async_get(pk="USER#123", sk="PROFILE")
await user.async_save()
await user.async_update(name="Jane")
await user.async_delete()

# Async iteration
async for user in User.async_query(hash_key="USER#123"):
    print(user.name)
```

### Pydantic Integration

```python
from pydantic import BaseModel, EmailStr
from pydynox import DynamoDBClient
from pydynox.integrations.pydantic import dynamodb_model

client = DynamoDBClient()

@dynamodb_model(table="users", hash_key="pk", range_key="sk", client=client)
class User(BaseModel):
    pk: str
    sk: str
    name: str
    email: EmailStr
    age: int = 0

# Pydantic validation works
user = User(pk="USER#123", sk="PROFILE", name="John", email="john@test.com")
user.save()

# Get
user = User.get(pk="USER#123", sk="PROFILE")
```

### S3 attribute (large files)

DynamoDB has a 400KB item limit. `S3Attribute` stores files in S3 and keeps metadata in DynamoDB. Upload on save, download on demand, delete when the item is deleted.

```python
from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute, S3Attribute, S3File

class Document(Model):
    model_config = ModelConfig(table="documents")
    
    pk = StringAttribute(hash_key=True)
    content = S3Attribute(bucket="my-bucket", prefix="docs/")

# Upload (async)
doc = Document(pk="DOC#1")
doc.content = S3File(b"...", name="report.pdf", content_type="application/pdf")
await doc.save()

# Download (async)
doc = await Document.get(pk="DOC#1")
data = await doc.content.get_bytes()           # Load to memory
await doc.content.save_to("/path/to/file.pdf") # Stream to file
url = await doc.content.presigned_url(3600)    # Share via URL

# Sync versions (with sync_ prefix)
doc.content.sync_get_bytes()
doc.content.sync_save_to("/path/to/file.pdf")
doc.content.sync_presigned_url(3600)

# Metadata (no S3 call)
print(doc.content.size)
print(doc.content.content_type)

# Delete - removes from both DynamoDB and S3
await doc.delete()
```

## Table management

Table operations follow the async-first pattern. Async methods have no prefix, sync methods have `sync_` prefix.

```python
from pydynox import DynamoDBClient

client = DynamoDBClient()

# Async (default)
await client.create_table(
    "users",
    hash_key=("pk", "S"),
    range_key=("sk", "S"),
    wait=True,
)

if await client.table_exists("users"):
    print("Table exists")

await client.delete_table("users")

# From Model
await User.create_table(wait=True)
if await User.table_exists():
    print("Table exists")
```

For sync code, use the `sync_` prefix:

```python
# Sync (use sync_ prefix)
client.sync_create_table("users", hash_key=("pk", "S"), wait=True)
client.sync_table_exists("users")
client.sync_delete_table("users")

# From Model
User.sync_create_table(wait=True)
User.sync_table_exists()
```

## Documentation

Full documentation: [https://leandrodamascena.github.io/pydynox](https://leandrodamascena.github.io/pydynox)

## License

MIT License

## Inspirations

This project was inspired by:

- [PynamoDB](https://github.com/pynamodb/PynamoDB) - The ORM-style API and model design
- [Pydantic](https://github.com/pydantic/pydantic) - Data validation patterns and integration approach
- [dynarust](https://github.com/Anexen/dynarust) - Rust DynamoDB client patterns
- [dyntastic](https://github.com/nayaverdier/dyntastic) - Pydantic + DynamoDB integration ideas

## Building from Source

### Requirements

- Python 3.11+
- Rust 1.70+
- maturin

### Setup

```bash
# Clone the repo
git clone https://github.com/leandrodamascena/pydynox.git
cd pydynox

# Install maturin
pip install maturin

# Build and install locally
maturin develop

# Or with uv
uv run maturin develop
```

### Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest
```
