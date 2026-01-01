# pydynox

A fast DynamoDB ORM for Python with a Rust core.

pydynox lets you work with DynamoDB using Python classes instead of raw dictionaries. The heavy lifting (serialization, deserialization) happens in Rust, so it's fast.

## Key features

- **Fast serialization** - Rust handles the heavy lifting
- **Simple API** - Define models like Django or SQLAlchemy
- **Type hints** - Full IDE support with autocomplete
- **Rate limiting** - Control throughput to avoid throttling
- **Lifecycle hooks** - Run code before/after operations
- **TTL support** - Auto-delete items after expiration
- **Pydantic integration** - Use your existing Pydantic models

## Getting started

### Installation

=== "pip"
    ```bash
    pip install pydynox
    ```

=== "uv"
    ```bash
    uv add pydynox
    ```

For Pydantic support:

```bash
pip install pydynox[pydantic]
```

### Define a model

A model is a Python class that maps to a DynamoDB table. You define attributes with their types, and pydynox handles the rest:

=== "basic_model.py"
    ```python
    --8<-- "docs/examples/models/basic_model.py"
    ```

### CRUD operations

Once you have a model, you can create, read, update, and delete items:

=== "crud_operations.py"
    ```python
    --8<-- "docs/examples/models/crud_operations.py"
    ```

That's it! You're now using DynamoDB with a clean, typed API.

## What's next?

Now that you have the basics, explore these guides:

### Core

| Guide | Description |
|-------|-------------|
| [Client](guides/client.md) | Configure the DynamoDB client |
| [Models](guides/models.md) | Attributes, keys, defaults, and CRUD operations |
| [Attributes](guides/attributes.md) | All available attribute types |
| [Indexes](guides/indexes.md) | Query by non-key attributes with GSIs |
| [Conditions](guides/conditions.md) | Filter and conditional writes |
| [Atomic updates](guides/atomic-updates.md) | Increment, append, and other atomic operations |
| [Observability](guides/observability.md) | Logging and metrics |

### Operations

| Guide | Description |
|-------|-------------|
| [Async support](guides/async.md) | Async/await for high-concurrency apps |
| [Batch operations](guides/batch.md) | Work with multiple items at once |
| [Transactions](guides/transactions.md) | All-or-nothing operations |
| [Tables](guides/tables.md) | Create and manage tables |

### Features

| Guide | Description |
|-------|-------------|
| [Lifecycle hooks](guides/hooks.md) | Run code before/after operations |
| [Rate limiting](guides/rate-limiting.md) | Control throughput |
| [Encryption](guides/encryption.md) | Field-level encryption with KMS |
| [Size calculator](guides/size-calculator.md) | Calculate item sizes |

### Integrations

| Guide | Description |
|-------|-------------|
| [Pydantic](guides/pydantic.md) | Use Pydantic models |

### Troubleshooting

| Guide | Description |
|-------|-------------|
| [Exceptions](guides/exceptions.md) | Error handling |
| [IAM permissions](guides/iam-permissions.md) | Required AWS permissions |
