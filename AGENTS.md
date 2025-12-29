# AI Agent Instructions

This file helps AI coding assistants understand the pydynox project.

## What is pydynox?

A fast DynamoDB ORM for Python. The core is written in Rust for speed, with Python bindings via PyO3.

## Project Structure

This is an example of the structure. The project may have more files. Follow this pattern when adding new ones.

```
pydynox/
├── src/                    # Rust code
│   ├── lib.rs             # Main module, exports to Python
│   ├── client.rs          # DynamoDB client
│   ├── basic_operations.rs # put, get, delete, update, query
│   ├── batch_operations.rs # batch_write, batch_get
│   └── transaction_operations.rs # transact_write
├── python/pydynox/        # Python wrappers
│   ├── __init__.py        # Public API exports
│   ├── client.py          # DynamoDBClient wrapper
│   ├── query.py           # QueryResult wrapper
│   └── transaction.py     # Transaction wrapper
├── tests/
│   ├── integration/       # Integration tests (need moto server)
│   └── python/            # Unit tests
└── Cargo.toml             # Rust dependencies
```

## Critical: How to Build

**NEVER use `cargo build`**. This is a PyO3 project. Use maturin:

```bash
# Development build
uv run maturin develop

# Release build (faster)
uv run maturin develop --release

# Build wheel for distribution
uv run maturin build --release
```

## How to Run Tests

```bash
# All tests
uv run pytest tests/ -v

# Specific test file
uv run pytest tests/integration/operations/test_get_item.py -v

# Skip benchmarks
uv run pytest tests/ -v --ignore=tests/benchmark
```

Tests use moto server (DynamoDB mock). The conftest.py starts it automatically.

## Code Style

### Rust

- Run `cargo fmt` before committing
- Run `cargo clippy -- -D warnings` to check for issues
- Add doc comments (`///`) to all public items
- Use `PyResult<T>` for functions that can fail

### Python

- Follow PEP 8
- Use type hints everywhere
- Use Google-style docstrings
- Use plain functions for tests, not classes
- Use `pytest.mark.parametrize` for multiple test cases

## Adding a New Feature

1. Write Rust code in `src/`
2. Export in `src/lib.rs`
3. Create Python wrapper in `python/pydynox/`
4. Export in `python/pydynox/__init__.py`
5. Write tests in `tests/`

## Python ↔ Rust Mapping

| Python | Rust |
|--------|------|
| `client.py` | `client.rs` |
| `query.py` | `basic_operations.rs` |
| `transaction.py` | `transaction_operations.rs` |

## Importing Rust from Python

```python
from pydynox import pydynox_core

# Use Rust classes
client = pydynox_core.DynamoDBClient(...)
```

Never import from `_rust` or other private modules.

## Common Mistakes to Avoid

1. **Using `cargo build`** - Won't produce a usable Python module
2. **Forgetting to export in `__init__.py`** - Users can't import it
3. **Using test classes** - Use plain functions instead
4. **Missing type hints** - Add them to all Python code
5. **Missing doc comments** - Add them to all public Rust items

## Writing Style

- Write simple English
- Short sentences
- No buzzwords (don't say "leverage", "utilize", "robust", etc.)
- Be direct and clear

## Useful Commands

```bash
# Format Rust code
cargo fmt

# Check Rust code
cargo clippy -- -D warnings

# Lint Python code
uv run ruff check python/ tests/

# Run specific test
uv run pytest tests/integration/operations/test_get_item.py -v

# Build release
uv run maturin develop --release
```

## Dependencies

- Rust: aws-sdk-dynamodb, pyo3, tokio
- Python: pytest, moto, boto3, hypothesis
