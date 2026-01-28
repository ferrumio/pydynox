# pydynox 🐍⚙️

[![CI](https://github.com/ferrumio/pydynox/actions/workflows/ci.yml/badge.svg)](https://github.com/ferrumio/pydynox/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/pydynox.svg)](https://pypi.org/project/pydynox/)
[![Python versions](https://img.shields.io/pypi/pyversions/pydynox.svg)](https://pypi.org/project/pydynox/)
[![License](https://img.shields.io/pypi/l/pydynox.svg)](https://github.com/ferrumio/pydynox/blob/main/LICENSE)
[![Downloads](https://static.pepy.tech/badge/pydynox/month)](https://pepy.tech/project/pydynox)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/ferrumio/pydynox/badge)](https://securityscorecards.dev/viewer/?uri=github.com/ferrumio/pydynox)

A fast, async-first DynamoDB ORM for Python with a Rust core.

> 📢 **Stable Release: March 2-6, 2026** - We're in the final stretch! The API is stabilizing, performance is being polished, and we're building the remaining features. We might release earlier if everything goes well. Stay tuned!

## Why pydynox?

**Py**(thon) + **Dyn**(amoDB) + **Ox**(ide/Rust)

## Key features

- **Async-first** - Async by default, sync with `sync_` prefix. True non-blocking I/O with Rust's tokio
- **Fast** - Rust core for serialization, compression, and encryption. Zero Python runtime dependencies
- **Simple API** - Class-based models like PynamoDB. Define once, use everywhere
- **Type-safe** - Full type hints for IDE autocomplete and type checkers
- **Pydantic support** - Use your existing Pydantic models with DynamoDB
- **Batteries included** - TTL, hooks, auto-generate, optimistic locking, rate limiting, encryption, compression, S3 attributes, PartiQL, observability

## Installation

```bash
pip install pydynox
```

Optional extras:

```bash
pip install pydynox[pydantic]       # Pydantic integration
pip install pydynox[opentelemetry]  # OpenTelemetry tracing
```

## Quick start

### Define a model

```python
from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute, NumberAttribute

class User(Model):
    model_config = ModelConfig(table="users")
    
    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    name = StringAttribute()
    age = NumberAttribute(default=0)
```

### Async operations (default)

Async methods have no prefix. This is the default.

```python
import asyncio

async def main():
    # Create
    user = User(pk="USER#123", sk="PROFILE", name="John")
    await user.save()

    # Read
    user = await User.get(pk="USER#123", sk="PROFILE")

    # Update
    await user.update(name="Jane", age=30)

    # Query
    async for user in User.query(hash_key="USER#123"):
        print(user.name)

    # Delete
    await user.delete()

asyncio.run(main())
```

### Sync operations (use sync_ prefix)

For scripts, CLI tools, or code that doesn't need async.

```python
# Create
user = User(pk="USER#123", sk="PROFILE", name="John")
user.sync_save()

# Read
user = User.sync_get(pk="USER#123", sk="PROFILE")

# Update
user.sync_update(name="Jane", age=30)

# Query
for user in User.sync_query(hash_key="USER#123"):
    print(user.name)

# Delete
user.sync_delete()
```

## Async-first API

pydynox is async-first. Methods without prefix are async, methods with `sync_` prefix are sync.

| Async (default) | Sync |
|-----------------|------|
| `await model.save()` | `model.sync_save()` |
| `await model.delete()` | `model.sync_delete()` |
| `await model.update()` | `model.sync_update()` |
| `await Model.get()` | `Model.sync_get()` |
| `async for x in Model.query()` | `for x in Model.sync_query()` |
| `async for x in Model.scan()` | `for x in Model.sync_scan()` |
| `await Model.batch_get()` | `Model.sync_batch_get()` |
| `async with BatchWriter()` | `with SyncBatchWriter()` |

Why async? Python's GIL blocks threads during I/O. With async, your app can handle other work while waiting for DynamoDB. pydynox releases the GIL during network calls, so async operations are truly non-blocking.

## Conditions

```python
# Save only if item doesn't exist
await user.save(condition=User.pk.not_exists())

# Delete with condition
await user.delete(condition=User.version == 5)

# Combine with & (AND) and | (OR)
await user.save(condition=User.pk.not_exists() | (User.version == 1))
```

## Atomic updates

```python
# Increment
await user.update(atomic=[User.age.add(1)])

# Append to list
await user.update(atomic=[User.tags.append(["verified"])])

# Multiple operations
await user.update(atomic=[
    User.age.add(1),
    User.tags.append(["premium"]),
])
```

## Batch operations

```python
from pydynox import BatchWriter, SyncBatchWriter, DynamoDBClient

client = DynamoDBClient()

# Async (default)
async with BatchWriter(client, "users") as batch:
    for i in range(100):
        batch.put({"pk": f"USER#{i}", "sk": "PROFILE", "name": f"User {i}"})

# Sync
with SyncBatchWriter(client, "users") as batch:
    batch.put({"pk": "USER#1", "sk": "PROFILE", "name": "John"})
```

## Global Secondary Index

```python
from pydynox.indexes import GlobalSecondaryIndex

class User(Model):
    model_config = ModelConfig(table="users")
    
    pk = StringAttribute(hash_key=True)
    email = StringAttribute()
    
    email_index = GlobalSecondaryIndex(
        index_name="email-index",
        hash_key="email",
    )

# Async
async for user in User.email_index.query(hash_key="john@test.com"):
    print(user.name)

# Sync
for user in User.email_index.sync_query(hash_key="john@test.com"):
    print(user.name)
```

## Transactions

```python
from pydynox import DynamoDBClient, Transaction

client = DynamoDBClient()

async with Transaction(client) as tx:
    tx.put("users", {"pk": "USER#1", "sk": "PROFILE", "name": "John"})
    tx.put("orders", {"pk": "ORDER#1", "sk": "DETAILS", "user": "USER#1"})
```

## Pydantic integration

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

# Async (default)
user = User(pk="USER#123", sk="PROFILE", name="John", email="john@test.com")
await user.save()
user = await User.get(pk="USER#123", sk="PROFILE")

# Sync
user.sync_save()
user = User.sync_get(pk="USER#123", sk="PROFILE")
```

## S3 attribute (large files)

DynamoDB has a 400KB item limit. `S3Attribute` stores files in S3 and keeps metadata in DynamoDB.

```python
from pydynox.attributes import S3Attribute, S3File

class Document(Model):
    model_config = ModelConfig(table="documents")
    
    pk = StringAttribute(hash_key=True)
    content = S3Attribute(bucket="my-bucket", prefix="docs/")

# Upload
doc = Document(pk="DOC#1")
doc.content = S3File(b"...", name="report.pdf", content_type="application/pdf")
await doc.save()

# Download (async)
data = await doc.content.get_bytes()
await doc.content.save_to("/path/to/file.pdf")
url = await doc.content.presigned_url(3600)

# Download (sync)
data = doc.content.sync_get_bytes()
doc.content.sync_save_to("/path/to/file.pdf")
```

## Table management

```python
# Async (default)
await User.create_table(wait=True)
if await User.table_exists():
    print("Table exists")

# Sync
User.sync_create_table(wait=True)
if User.sync_table_exists():
    print("Table exists")
```

## GenAI contributions 🤖

I believe GenAI is transforming how we build software. It's a powerful tool that accelerates development when used by developers who understand what they're doing.

To support both humans and AI agents, I created:

- `.ai/` folder - Guidelines for agentic IDEs (Cursor, Windsurf, Kiro, etc.)
- `ADR/` folder - Architecture Decision Records for humans to understand the "why" behind decisions

**If you're contributing with AI help:**

- Understand what the AI generated before submitting
- Make sure the code follows the project patterns
- Test your changes

I reserve the right to reject low-quality PRs where project patterns are not followed and it's clear that GenAI was driving instead of the developer.

## Documentation

Full documentation: [https://ferrumio.github.io/pydynox](https://ferrumio.github.io/pydynox)

## License

Apache 2.0 License

## Inspirations

- [PynamoDB](https://github.com/pynamodb/PynamoDB) - The ORM-style API and model design
- [Pydantic](https://github.com/pydantic/pydantic) - Data validation patterns
- [dynarust](https://github.com/Anexen/dynarust) - Rust DynamoDB client patterns
- [dyntastic](https://github.com/nayaverdier/dyntastic) - Pydantic + DynamoDB integration ideas

## Building from source

```bash
# Clone
git clone https://github.com/ferrumio/pydynox.git
cd pydynox

# Build (requires Python 3.11+, Rust 1.70+)
pip install maturin
maturin develop

# Test
pip install -e ".[dev]"
pytest
```
