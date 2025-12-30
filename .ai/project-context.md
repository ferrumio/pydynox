# Project Context

## What is pydynox?

A fast DynamoDB ORM for Python. The name comes from:
- **Py** = Python
- **Dyn** = DynamoDB
- **Ox** = Oxide (Rust)

## Tech Stack

- **Rust core** - All the heavy work (serialization, compression, encryption)
- **PyO3** - Python bindings for Rust
- **maturin** - Build tool for PyO3 projects

## Performance Goal

This library aims to be SUPER fast. Speed is a core feature, not an afterthought.

Every decision about where code lives should consider performance. See `coding-guidelines.md` for details.

## Project Info

- License: MIT
- Hosted on: GitHub
- Status: Early development (not ready for production)

## Building the Project

**IMPORTANT**: This is a PyO3 project. Never use `cargo build` directly.

Always use maturin:

```bash
# Development build
uv run maturin develop

# Release build (faster)
uv run maturin develop --release

# Build wheel for distribution
uv run maturin build --release
```

The `cargo build` command will not produce a usable Python module. Only maturin knows how to build PyO3 bindings correctly.

## Project Structure

```
pydynox/
├── src/                    # Rust code
│   ├── lib.rs             # Main module, exports to Python
│   ├── client.rs          # DynamoDB client
│   ├── basic_operations.rs # put, get, delete, update, query
│   ├── batch_operations.rs # batch_write, batch_get
│   ├── transaction_operations.rs # transact_write
│   ├── serialization.rs   # Python <-> DynamoDB conversion
│   ├── compression.rs     # zstd compression
│   ├── encryption.rs      # AES encryption
│   └── errors.rs          # Custom error types
├── python/pydynox/        # Python wrappers
│   ├── __init__.py        # Public API exports
│   ├── model.py           # Model base class
│   ├── client.py          # DynamoDBClient wrapper
│   ├── attributes.py      # Field types
│   ├── exceptions.py      # Custom exceptions
│   └── integrations/      # Pydantic, etc.
├── tests/
│   ├── integration/       # Integration tests (need moto server)
│   └── python/            # Unit tests
├── Cargo.toml             # Rust dependencies
└── pyproject.toml         # Python config
```

## Public vs Internal API

The public API is what users import from `pydynox`. Keep it small and clean.

### What Goes in Public API

- `Model`, `ModelConfig` - The ORM classes users extend
- `DynamoDBClient` - The client users create
- `Condition`, `Action` - Query/update builders
- `QueryResult`, `BatchWriter`, `Transaction` - Operation helpers
- Attribute types like `StringAttribute`, `NumberAttribute`

### What Stays Internal

- Compression functions (`_compression.py`)
- Encryption functions (`_encryption.py`)
- Serialization helpers
- Size calculation internals

### Naming Convention

- Public modules: `model.py`, `client.py`, `query.py`
- Internal modules: `_compression.py`, `_encryption.py`
- Internal folder: `_internal/`

## Lambda Cold Start Note

This is important for AWS Lambda. Cold start happens once, then the same container handles many requests.

- **Cold start (once)**: Model class loading, field setup, client creation → Python is fine
- **Warm invocations (many)**: Serialize, query, save, transform → Must be Rust

Focus optimization on the hot path (warm invocations). That's where users feel the speed.
