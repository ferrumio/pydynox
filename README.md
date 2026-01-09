# pydynox 🐍⚙️

[![CI](https://github.com/leandrodamascena/pydynox/actions/workflows/ci.yml/badge.svg)](https://github.com/leandrodamascena/pydynox/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/pydynox.svg)](https://pypi.org/project/pydynox/)
[![Python versions](https://img.shields.io/pypi/pyversions/pydynox.svg)](https://pypi.org/project/pydynox/)
[![License](https://img.shields.io/pypi/l/pydynox.svg)](https://github.com/leandrodamascena/pydynox/blob/main/LICENSE)
[![Downloads](https://static.pepy.tech/badge/pydynox/month)](https://pepy.tech/project/pydynox)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/leandrodamascena/pydynox/badge)](https://securityscorecards.dev/viewer/?uri=github.com/leandrodamascena/pydynox)

A fast DynamoDB ORM for Python with a Rust core.

> **Pre-release**: The core features are working and tested. We're adding features, polishing the API, receiving ideas, and testing performance and edge cases before v1.0. Feel free to try it out and share feedback!

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
- Observability (logging, metrics)

## Installation

```bash
pip install pydynox
```

For Pydantic support:

```bash
pip install pydynox[pydantic]
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
user.save(condition=User.pk.does_not_exist())

# Delete with condition
user.delete(condition=User.version == 5)

# Combine conditions with & (AND) and | (OR)
user.save(
    condition=User.pk.does_not_exist() | (User.version == 1)
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
- `User.field.does_not_exist()` - attribute does not exist
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
from pydynox import DynamoDBClient, Transaction

client = DynamoDBClient()

with Transaction(client) as tx:
    tx.put("users", {"pk": "USER#1", "sk": "PROFILE", "name": "John"})
    tx.put("orders", {"pk": "ORDER#1", "sk": "DETAILS", "user": "USER#1"})
    tx.delete("temp", {"pk": "TEMP#1"})
```

### Async Support

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

### S3 Attribute (Large Files)

DynamoDB has a 400KB item limit. `S3Attribute` stores files in S3 and keeps metadata in DynamoDB. Upload on save, download on demand, delete when the item is deleted.

```python
from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute, S3Attribute
from pydynox._internal._s3 import S3File

class Document(Model):
    model_config = ModelConfig(table="documents")
    
    pk = StringAttribute(hash_key=True)
    content = S3Attribute(bucket="my-bucket", prefix="docs/")

# Upload
doc = Document(pk="DOC#1")
doc.content = S3File(b"...", name="report.pdf", content_type="application/pdf")
doc.save()

# Download
doc = Document.get(pk="DOC#1")
data = doc.content.get_bytes()           # Load to memory
doc.content.save_to("/path/to/file.pdf") # Stream to file
url = doc.content.presigned_url(3600)    # Share via URL

# Metadata (no S3 call)
print(doc.content.size)
print(doc.content.content_type)

# Delete - removes from both DynamoDB and S3
doc.delete()
```

## Table Management

```python
from pydynox import DynamoDBClient

client = DynamoDBClient()

# Create table
client.create_table(
    "users",
    hash_key=("pk", "S"),
    range_key=("sk", "S"),
    wait=True,
)

# Create with on-demand billing (default)
client.create_table(
    "users",
    hash_key=("pk", "S"),
    billing_mode="PAY_PER_REQUEST",
)

# Create with provisioned capacity
client.create_table(
    "users",
    hash_key=("pk", "S"),
    billing_mode="PROVISIONED",
    read_capacity=10,
    write_capacity=5,
)

# Check if table exists
if not client.table_exists("users"):
    client.create_table("users", hash_key=("pk", "S"))

# Delete table
client.delete_table("users")
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
