# pydynox 🐍⚙️

[![CI](https://github.com/leandrodamascena/pydynox/actions/workflows/ci.yml/badge.svg)](https://github.com/leandrodamascena/pydynox/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/pydynox.svg)](https://pypi.org/project/pydynox/)
[![Python versions](https://img.shields.io/pypi/pyversions/pydynox.svg)](https://pypi.org/project/pydynox/)
[![License](https://img.shields.io/pypi/l/pydynox.svg)](https://github.com/leandrodamascena/pydynox/blob/main/LICENSE)

A fast DynamoDB ORM for Python with a Rust core.

> **Pre-release**: Core features are working and tested. We're polishing the API and testing edge cases before v1.0.

## Why pydynox?

**Py**(thon) + **Dyn**(amoDB) + **Ox**(ide/Rust)

- **Fast** - Rust handles serialization, compression, and encryption
- **Simple** - Class-based API like PynamoDB
- **Async first** - All operations have async versions
- **Type-safe** - Full type hints and mypy support
- **Zero dependencies** - Just the wheel, nothing else

## Installation

```bash
pip install pydynox
```

## Quick start

```python
from pydynox import Model, ModelConfig, DynamoDBClient
from pydynox.attributes import StringAttribute, NumberAttribute

client = DynamoDBClient(region="us-east-1")

class User(Model):
    model_config = ModelConfig(table="users", client=client)
    
    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    name = StringAttribute()
    age = NumberAttribute(default=0)

# Create
user = User(pk="USER#123", sk="PROFILE", name="John")
user.save()

# Read
user = User.get(pk="USER#123", sk="PROFILE")

# Update
user.name = "John Doe"
user.save()

# Delete
user.delete()
```

## Features

### Query and scan

```python
# Query by hash key
for user in User.query(hash_key="USER#123"):
    print(user.name)

# With range key condition
for user in User.query(hash_key="USER#123", range_key_condition=User.sk.begins_with("ORDER#")):
    print(user.name)

# Scan with filter
for user in User.scan(filter_condition=User.age >= 18):
    print(user.name)
```

### Conditions

```python
# Save only if item doesn't exist
user.save(condition=User.pk.does_not_exist())

# Delete with condition
user.delete(condition=User.version == 5)
```

### Atomic updates

```python
from pydynox._internal._atomic import increment, append

# Increment a number
user.update(atomic=[increment(User.age, 1)])

# Append to list
user.update(atomic=[append(User.tags, ["verified"])])
```

### Batch operations

```python
with User.batch_write() as batch:
    batch.save(user1)
    batch.save(user2)
    batch.delete(user3)
```

### Transactions

```python
with User.transaction() as tx:
    tx.save(user1)
    tx.delete(user2)
```

### Global secondary indexes

```python
from pydynox.indexes import GlobalSecondaryIndex

class User(Model):
    model_config = ModelConfig(table="users", client=client)
    
    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    email = StringAttribute()
    
    email_index = GlobalSecondaryIndex(hash_key="email")

# Query on index
for user in User.email_index.query(hash_key="john@test.com"):
    print(user.name)
```

### Async support ⚡

All operations have async versions. No extra dependencies needed.

```python
# CRUD
user = await User.async_get(pk="USER#123", sk="PROFILE")
await user.async_save()
await user.async_delete()

# Query and scan
async for user in User.async_query(hash_key="USER#123"):
    print(user.name)

async for user in User.async_scan(filter_condition=User.age >= 18):
    print(user.name)

# Batch and transactions work too
async with User.async_batch_write() as batch:
    await batch.save(user1)
    await batch.save(user2)
```

### TTL (auto-expiring items)

```python
from pydynox.attributes import TTLAttribute, ExpiresIn

class Session(Model):
    model_config = ModelConfig(table="sessions", client=client)
    
    pk = StringAttribute(hash_key=True)
    expires_at = TTLAttribute()

session = Session(pk="SESSION#123", expires_at=ExpiresIn.hours(1))
session.save()

# Check expiration
print(session.is_expired)
print(session.expires_in)
```

### Lifecycle hooks

```python
from pydynox.hooks import before_save, after_save

class User(Model):
    model_config = ModelConfig(table="users", client=client)
    
    pk = StringAttribute(hash_key=True)
    name = StringAttribute()
    
    @before_save
    def validate(self):
        if not self.name:
            raise ValueError("Name is required")
    
    @after_save
    def log_save(self):
        print(f"Saved {self.pk}")
```

### Auto-generate IDs and timestamps

```python
from pydynox import AutoGenerate
from pydynox.attributes import StringAttribute, DatetimeAttribute

class User(Model):
    model_config = ModelConfig(table="users", client=client)
    
    pk = StringAttribute(hash_key=True, default=AutoGenerate.uuid4())
    created_at = DatetimeAttribute(default=AutoGenerate.utc_now())
```

### Optimistic locking

```python
from pydynox.attributes import VersionAttribute

class User(Model):
    model_config = ModelConfig(table="users", client=client)
    
    pk = StringAttribute(hash_key=True)
    name = StringAttribute()
    version = VersionAttribute()

# Version is auto-incremented on save
# Raises ConditionCheckFailedError if version mismatch
```

### Rate limiting

```python
from pydynox import ModelConfig
from pydynox.rate_limit import RateLimitConfig

config = ModelConfig(
    table="users",
    client=client,
    rate_limit=RateLimitConfig(rcu=100, wcu=50),
)
```

### Field encryption (KMS)

```python
from pydynox.attributes import EncryptedAttribute

class User(Model):
    model_config = ModelConfig(table="users", client=client)
    
    pk = StringAttribute(hash_key=True)
    ssn = EncryptedAttribute(key_id="alias/my-key")
```

### Compression

```python
from pydynox.attributes import CompressedAttribute

class Document(Model):
    model_config = ModelConfig(table="documents", client=client)
    
    pk = StringAttribute(hash_key=True)
    body = CompressedAttribute()  # Uses zstd by default
```

### S3 attribute (large files)

DynamoDB has a 400KB item limit. A common pattern is to store files in S3 and keep metadata in DynamoDB. `S3Attribute` handles this automatically: upload on save, download on demand, delete when the item is deleted.

```python
from pydynox.attributes import S3Attribute
from pydynox._internal._s3 import S3File

class Document(Model):
    model_config = ModelConfig(table="documents", client=client)
    
    pk = StringAttribute(hash_key=True)
    name = StringAttribute()
    content = S3Attribute(bucket="my-bucket", prefix="docs/")

# Upload - file goes to S3, metadata to DynamoDB
doc = Document(pk="DOC#1", name="report.pdf")
doc.content = S3File(b"...", name="report.pdf", content_type="application/pdf")
doc.save()

# Download
doc = Document.get(pk="DOC#1")
data = doc.content.get_bytes()           # Load to memory
doc.content.save_to("/path/to/file.pdf") # Stream to file (large files)
url = doc.content.presigned_url(3600)    # Share via URL

# Metadata always available (no S3 call)
print(doc.content.size)          # File size in bytes
print(doc.content.content_type)  # MIME type

# Delete - removes from both DynamoDB and S3
doc.delete()
```

### PartiQL support

```python
users = User.execute_statement(
    "SELECT * FROM users WHERE pk = ?",
    parameters=["USER#123"]
)
```

### Observability

```python
from pydynox import set_logger
import logging

# Enable logging
set_logger(logging.getLogger("pydynox"))

# Get operation metrics
user.save()
metrics = User.get_last_metrics()
print(f"Duration: {metrics.duration_ms}ms")
print(f"Consumed WCU: {metrics.consumed_wcu}")
```

### Pydantic integration

```bash
pip install pydynox[pydantic]
```

```python
from pydynox import dynamodb_model
from pydantic import BaseModel

@dynamodb_model(table="users", hash_key="pk")
class User(BaseModel):
    pk: str
    name: str
    age: int = 0

user = User(pk="USER#123", name="John")
user.save()
```

## Documentation

Full docs: [https://leandrodamascena.github.io/pydynox](https://leandrodamascena.github.io/pydynox)

## GenAI contributions 🤖

I believe GenAI is changing how we build software. To support both humans and AI agents:

- `.ai/` folder - Guidelines for agentic IDEs (Cursor, Windsurf, Kiro, etc.)
- `ADR/` folder - Architecture Decision Records

If you're contributing with AI help, understand what the AI generated before submitting. I reserve the right to reject PRs where project patterns are not followed.

## Building from source

```bash
# Clone
git clone https://github.com/leandrodamascena/pydynox.git
cd pydynox

# Build with maturin (required for PyO3)
pip install maturin
maturin develop

# Or with uv
uv run maturin develop

# Run tests
uv run pytest
```

## License

Apache 2.0

## Inspirations

- [PynamoDB](https://github.com/pynamodb/PynamoDB) - ORM-style API
- [Pydantic](https://github.com/pydantic/pydantic) - Data validation patterns
- [dynarust](https://github.com/Anexen/dynarust) - Rust DynamoDB patterns
