# pydynox 🐍⚙️

[![CI](https://github.com/leandrodamascena/pydynox/actions/workflows/ci.yml/badge.svg)](https://github.com/leandrodamascena/pydynox/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/pydynox.svg)](https://pypi.org/project/pydynox/)
[![Python versions](https://img.shields.io/pypi/pyversions/pydynox.svg)](https://pypi.org/project/pydynox/)
[![License](https://img.shields.io/pypi/l/pydynox.svg)](https://github.com/leandrodamascena/pydynox/blob/main/LICENSE)
[![Downloads](https://static.pepy.tech/badge/pydynox/month)](https://pepy.tech/project/pydynox)

A fast DynamoDB ORM for Python with a Rust core.

> ⚠️ **Early Development**: This project is not ready for production yet. The API may change before v1.0.
>
> We welcome feedback and contributions! Check the [open issues](https://github.com/leandrodamascena/pydynox/issues) to see what's planned or to share your ideas.

## Why "pydynox"?

**Py**(thon) + **Dyn**(amoDB) + **Ox**(ide/Rust)

## GenAI Contributions 🤖

This project welcomes GenAI-assisted contributions! Parts of the code and docstrings were written with AI help.

If you're using AI tools to contribute, check the `.ai/` folder. It has all the guidelines:

- `.ai/README.md` - Quick start for AI agents
- `.ai/project-context.md` - What is pydynox, tech stack
- `.ai/coding-guidelines.md` - Code style, Python vs Rust decisions
- `.ai/testing-guidelines.md` - How to write tests
- `.ai/common-mistakes.md` - Things that break the build

**Rules for AI-assisted contributions:**

- Follow the project's coding style and patterns
- Make sure the code makes sense and is tested
- Don't submit random or low-quality generated code
- Review and understand what the AI generated before submitting

## Features

- Simple class-based API like PynamoDB
- Fast serialization with Rust
- Batch operations with auto-splitting
- Transactions
- Global Secondary Indexes
- Async support
- Pydantic integration

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
from pydynox import Model, ModelConfig, String, Number, Boolean, List

class User(Model):
    model_config = ModelConfig(table="users")
    
    pk = String(hash_key=True)
    sk = String(range_key=True)
    name = String()
    email = String()
    age = Number(default=0)
    active = Boolean(default=True)
    tags = List(String)
```

### CRUD Operations

```python
# Create
user = User(pk="USER#123", sk="PROFILE", name="John", email="john@test.com")
user.save()

# Read
user = User.get(pk="USER#123", sk="PROFILE")

# Update
user.name = "John Doe"
user.save()

# Delete
user.delete()
```

### Query

```python
from pydynox import Condition

# Simple query
users = User.query(pk="USER#123")

# With filters
users = User.query(pk="USER#123") \
    .where(Condition.begins_with("sk", "ORDER#")) \
    .where(Condition.gt("age", 18)) \
    .exec()

# Iterate (auto pagination)
for user in users:
    print(user.name)
```

### Conditions

```python
from pydynox import Condition

# Save with condition
user.save(condition=Condition.not_exists("pk"))

# Delete with condition
user.delete(condition=Condition.eq("version", 5))

# Combine conditions
user.save(
    condition=Condition.not_exists("pk") | Condition.eq("version", 1)
)
```

Available conditions:
- `Condition.eq(field, value)` - equals
- `Condition.ne(field, value)` - not equals
- `Condition.gt(field, value)` - greater than
- `Condition.gte(field, value)` - greater than or equal
- `Condition.lt(field, value)` - less than
- `Condition.lte(field, value)` - less than or equal
- `Condition.exists(field)` - attribute exists
- `Condition.not_exists(field)` - attribute does not exist
- `Condition.begins_with(field, prefix)` - string starts with
- `Condition.contains(field, value)` - string or list contains
- `Condition.between(field, low, high)` - value in range

### Atomic Updates

```python
from pydynox import Action

# Simple set
user.update(name="New Name", email="new@test.com")

# Increment a number
user.update(Action.increment("age", 1))

# Append to list
user.update(Action.append("tags", ["verified"]))

# Remove field
user.update(Action.remove("temp_field"))

# Combine with condition
user.update(
    Action.increment("age", 1),
    condition=Condition.eq("status", "active")
)
```

### Batch Operations

```python
# Batch write
with User.batch_write() as batch:
    batch.save(user1)
    batch.save(user2)
    batch.delete(user3)

# Batch get
users = User.batch_get([
    ("USER#1", "PROFILE"),
    ("USER#2", "PROFILE"),
])
```

### Global Secondary Index

```python
from pydynox import GlobalIndex, ModelConfig

class User(Model):
    model_config = ModelConfig(table="users")
    
    pk = String(hash_key=True)
    sk = String(range_key=True)
    email = String()
    
    email_index = GlobalIndex(hash_key="email")

# Query on index
users = User.email_index.query(email="john@test.com")
```

### Transactions

```python
with User.transaction() as tx:
    tx.save(user1)
    tx.delete(user2)
    tx.update(user3, Action.increment("age", 1))
```

### Async Support

```python
# All methods work with await
user = await User.get(pk="USER#123", sk="PROFILE")
await user.save()

async for user in User.query(pk="USER#123"):
    print(user.name)
```

### Pydantic Integration

```python
from pydynox import dynamodb_model
from pydantic import BaseModel, EmailStr

@dynamodb_model(table="users", hash_key="pk", range_key="sk")
class User(BaseModel):
    pk: str
    sk: str
    name: str
    email: EmailStr
    age: int = 0

# All pydynox methods available
user = User(pk="USER#123", sk="PROFILE", name="John", email="john@test.com")
user.save()
```

## Table Management

```python
# Create table
User.create_table()

# Create with custom capacity
User.create_table(read_capacity=10, write_capacity=5)

# Create with on-demand billing
User.create_table(billing_mode="PAY_PER_REQUEST")

# Check if table exists
if not User.table_exists():
    User.create_table()

# Delete table
User.delete_table()
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
