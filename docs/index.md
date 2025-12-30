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

| Guide | Description |
|-------|-------------|
| [Models](guides/models.md) | Learn about attributes, keys, and defaults |
| [CRUD operations](guides/crud.md) | More on create, read, update, delete |
| [Batch operations](guides/batch.md) | Work with multiple items at once |
| [Transactions](guides/transactions.md) | All-or-nothing operations |
| [Rate limiting](guides/rate-limiting.md) | Control throughput |
| [Lifecycle hooks](guides/hooks.md) | Run code before/after operations |
| [TTL](guides/ttl.md) | Auto-delete items |
| [Pydantic](guides/pydantic.md) | Use Pydantic models |
