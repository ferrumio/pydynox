# Coding Guidelines

## Rust vs Python Decision

This library aims to be SUPER fast. Every decision about where code lives should consider performance.

### When to Use Rust

Put code in Rust when:

1. **Serialization/Deserialization** - Converting Python objects to DynamoDB format and back
2. **Data transformation** - Any loop that processes items, transforms data, or builds requests
3. **Compression/Encryption** - CPU-heavy work that blocks Python's GIL
4. **Batch processing** - Splitting large batches, merging results, handling retries
5. **Validation** - Schema validation, type checking, size calculations
6. **String operations** - Building expressions, handling reserved words, escaping

### When to Use Python

Keep code in Python when:

1. **API surface** - The public classes and methods users interact with
2. **Configuration** - ModelConfig, field definitions, decorators (run once at import time)
3. **Async coordination** - Python's asyncio for managing concurrent operations
4. **Error messages** - User-facing errors with helpful context
5. **Thin wrappers** - Simple functions that just call Rust and return results

### Decision Checklist

1. Does this code run on every request? → Rust
2. Does this code loop over data? → Rust
3. Does this code block while processing? → Rust
4. Does this code only run at import/setup time? → Python is fine
5. Is this just glue code between user and Rust? → Python is fine

### Where Things Live

| Feature | Python | Rust | Why |
|---------|--------|------|-----|
| Model class definition | ✓ | | Runs once at import |
| Field type definitions | ✓ | | Configuration only |
| Serialize model to DynamoDB | | ✓ | Every save/update |
| Deserialize DynamoDB to model | | ✓ | Every get/query |
| Build condition expressions | | ✓ | String processing |
| Calculate item size | | ✓ | Loops over attributes |
| Compress attributes | | ✓ | CPU-heavy |
| Encrypt fields | | ✓ | CPU-heavy |
| Rate limiting logic | | ✓ | Runs on every request |
| Batch splitting | | ✓ | Loops and transforms |

---

## Rust Code Style

### File Organization

```
pydynox/src/
├── lib.rs                    # Module exports and PyO3 module definition
├── client.rs                 # DynamoDBClient struct and methods
├── basic_operations.rs       # get, put, delete, query, scan
├── batch_operations.rs       # batch_write, batch_get
├── transaction_operations.rs # transact_write, transact_get
├── table_operations.rs       # create_table, delete_table
├── serialization.rs          # Python <-> DynamoDB conversion
├── compression.rs            # zstd compression
├── encryption.rs             # AES encryption
├── rate_limiter.rs           # Rate limiting logic
└── errors.rs                 # Custom error types
```

### PyO3 Patterns

Exposing classes to Python:

```rust
use pyo3::prelude::*;

#[pyclass]
pub struct DynamoDBClient {
    // fields
}

#[pymethods]
impl DynamoDBClient {
    #[new]
    pub fn new(region: Option<String>) -> PyResult<Self> {
        // constructor
    }

    pub fn get_item(&self, table: &str, key: PyObject) -> PyResult<Option<PyObject>> {
        // method
    }
}
```

Registering in lib.rs:

```rust
#[pymodule]
fn pydynox_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<DynamoDBClient>()?;
    m.add_function(wrap_pyfunction!(serialize, m)?)?;
    Ok(())
}
```

### Error Handling & Exceptions

All pydynox exceptions inherit from `PydynoxError`:

```
PydynoxError (base)
├── TableNotFoundError      # DynamoDB ResourceNotFoundException
├── TableAlreadyExistsError # DynamoDB ResourceInUseException
├── ValidationError         # DynamoDB ValidationException
├── ConditionCheckFailedError # DynamoDB ConditionalCheckFailedException
├── TransactionCanceledError  # DynamoDB TransactionCanceledException
├── ThrottlingError         # DynamoDB ProvisionedThroughputExceededException
├── AccessDeniedError       # DynamoDB/KMS AccessDeniedException
├── CredentialsError        # AWS credential issues
├── SerializationError      # Data conversion errors
├── ConnectionError         # Network/endpoint issues
├── EncryptionError         # KMS/encryption errors
└── ItemTooLargeError       # Item exceeds size limit (Python-only)
```

#### Creating Exceptions in Rust

Use `create_exception!` macro from PyO3:

```rust
// In errors.rs
use pyo3::create_exception;
use pyo3::exceptions::PyException;

// Base exception
create_exception!(pydynox, PydynoxError, PyException);

// Specific exceptions inherit from PydynoxError
create_exception!(pydynox, TableNotFoundError, PydynoxError);
create_exception!(pydynox, ValidationError, PydynoxError);
```

#### Registering Exceptions

Exceptions must be registered in `lib.rs`:

```rust
// In errors.rs
pub fn register_exceptions(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("PydynoxError", m.py().get_type::<PydynoxError>())?;
    m.add("TableNotFoundError", m.py().get_type::<TableNotFoundError>())?;
    Ok(())
}

// In lib.rs
#[pymodule]
fn pydynox_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    errors::register_exceptions(m)?;
    Ok(())
}
```

#### Mapping DynamoDB Errors

DynamoDB errors must be mapped to our custom exceptions:

```rust
use crate::errors::map_sdk_error;

pub fn get_item(&self, table: &str, key: PyObject) -> PyResult<Option<PyObject>> {
    let result = self.runtime.block_on(async {
        self.client.get_item()
            .table_name(table)
            .send()
            .await
    });

    match result {
        Ok(output) => { /* convert to Python */ }
        Err(e) => Err(map_sdk_error(e, Some(table)))
    }
}
```

For KMS operations, use `map_kms_error()`:

```rust
let result = kms_client.encrypt(...).await;
match result {
    Ok(output) => { /* ... */ }
    Err(e) => Err(map_kms_error(e))
}
```

#### Internal Errors

For internal errors (not from DynamoDB), use `PyRuntimeError`:

```rust
use pyo3::exceptions::PyRuntimeError;

fn decompress(data: &[u8]) -> PyResult<Vec<u8>> {
    zstd::decode_all(data)
        .map_err(|e| PyRuntimeError::new_err(format!("Decompression failed: {}", e)))
}
```

#### Adding a New Exception

1. Add `create_exception!` in `errors.rs`:
```rust
create_exception!(pydynox, NewError, PydynoxError);
```

2. Register it in `register_exceptions()`:
```rust
m.add("NewError", m.py().get_type::<NewError>())?;
```

3. Re-export in Python `exceptions.py`:
```python
NewError = pydynox_core.NewError
```

#### Rules

- DynamoDB/AWS errors → Use `map_sdk_error()` or `map_kms_error()`
- Internal errors (compression, parsing) → Use `PyRuntimeError`
- Never let raw AWS SDK errors bubble up to Python

#### Using Exceptions in Python

```python
from pydynox.exceptions import (
    PydynoxError,
    TableNotFoundError,
    ConditionCheckFailedError,
)

# Catch specific error
try:
    user = User.get(pk="USER#123")
except TableNotFoundError:
    print("Table doesn't exist")
except ConditionCheckFailedError:
    print("Condition failed")

# Catch all pydynox errors
try:
    user.save()
except PydynoxError as e:
    print(f"DynamoDB error: {e}")
```

Always import from `pydynox.exceptions`, not directly from `pydynox_core`.

### Doc Comments

Every public item needs doc comments:

```rust
/// Serialize a Python object to DynamoDB AttributeValue format.
///
/// # Arguments
///
/// * `py` - Python interpreter
/// * `value` - The Python object to serialize
///
/// # Returns
///
/// A dict representing the DynamoDB item
pub fn serialize(py: Python<'_>, value: PyObject) -> PyResult<PyObject> {
    // ...
}
```

### Performance Tips

1. **Avoid cloning** - Use references when possible
2. **Reuse buffers** - Don't allocate on every call
3. **Release GIL** - Use `py.allow_threads()` for CPU-heavy work
4. **Batch operations** - Process multiple items in one Rust call

```rust
// Release GIL for CPU work
pub fn compress(&self, py: Python<'_>, data: &[u8]) -> PyResult<Vec<u8>> {
    py.allow_threads(|| {
        zstd::encode_all(data, 3)
    }).map_err(to_py_err)
}
```

---

## Python Code Style

### File Organization

```
pydynox/python/pydynox/
├── __init__.py          # Public exports only
├── model.py             # Model base class
├── client.py            # DynamoDBClient wrapper
├── config.py            # ModelConfig and settings
├── attributes.py        # Field types
├── query.py             # Query builder
├── exceptions.py        # Custom exceptions
├── _internal/           # Internal helpers
│   ├── __init__.py
│   ├── _compression.py  # Internal: compression
│   └── _encryption.py   # Internal: encryption
└── integrations/        # Pydantic, etc.
```

### Duplication (DRY) and code quality

Duplicated code is **harder to keep correct** (fixes must be applied everywhere) and **noisier in review**. Automated checks and team standards often treat high duplication in new changes as a problem—plan for that up front when you add or change Python:

1. **Do not copy-paste** the same control flow, conditionals, or config lookups in multiple modules. If you are about to paste a second time, **extract a helper** (module-level function, or a small method on the relevant base class like `ModelBase`).
2. **Reuse existing hooks** where they exist — for example config resolution and hook behavior should go through the established paths (`_get_config()`, `_get_consistent_read`, `_run_after_load_hook`, etc.) instead of inlining new variants.
3. **Similar tests** in one file: prefer **`@pytest.mark.parametrize`** or shared fixtures over many nearly identical test functions.
4. If a change *must* look similar in two places (e.g. sync vs async), keep the **shared logic in one function** and keep the call sites as thin as possible.

Refactor early when the same block appears more than once; do not wait for a failing check or a large follow-up PR.

### Type Hints

Always use type hints. mypy MUST pass with zero errors.

```python
# Good
def get_item(self, pk: str, sk: Optional[str] = None) -> Optional["Model"]:
    ...

# Bad - mypy will fail
def get_item(self, pk, sk=None):
    ...
```

Use `from __future__ import annotations` at the top of files.

#### mypy Rules

- All functions must have type hints for parameters and return values
- Use `# type: ignore` only when absolutely necessary, and add a comment explaining why
- Avoid `Any` type when possible. If you must use it, be specific about why
- Run `uv run mypy .` before committing

### Docstrings

Use Google style:

```python
def save(self, condition: Optional[Condition] = None) -> None:
    """Save the model to DynamoDB.

    Args:
        condition: Optional condition that must be true for the write.

    Raises:
        ConditionFailedError: If the condition is not met.

    Example:
        user = User(pk="USER#1", name="John")
        user.save()
    """
```

### Imports

Order imports like this (ruff will enforce this):

1. Standard library
2. Third party
3. Local imports (pydynox)

```python
from __future__ import annotations

import json
from typing import Any, Optional

from pydynox import pydynox_core
from pydynox.exceptions import ItemNotFoundError
```

Run `uv run ruff check --fix .` to auto-fix import ordering.

### Calling Rust

Always go through `pydynox_core`:

```python
from pydynox import pydynox_core

# Good
result = pydynox_core.serialize(data)

# Bad - don't do this
from pydynox.pydynox_core import serialize
```

### Optional Dependencies

Optional dependencies (like Pydantic) must only be imported when the feature is used:

```python
# Bad - breaks if pydantic not installed
from pydantic import BaseModel

# Good - import inside the function
def dynamodb_model(table: str, hash_key: str):
    try:
        from pydantic import BaseModel
    except ImportError:
        raise ImportError(
            "Pydantic integration requires pydantic. "
            "Install with: pip install pydynox[pydantic]"
        )
```

---

## Code Quality Requirements

All Python code MUST pass these checks before commit:

```bash
uv run ruff check .          # Linting - must pass with zero errors
uv run ruff format --check . # Formatting - must be formatted
uv run mypy .                # Type checking - must pass with zero errors
```

These are not optional. Fix all errors before submitting code.

### Pre-commit Checklist

Before committing Python code:

1. `uv run ruff format .` - Format code
2. `uv run ruff check --fix .` - Fix lint errors
3. `uv run mypy .` - Check types
4. `uv run pytest` - Run tests

All four must pass. No exceptions.

---

## Useful Commands

```bash
# Format Rust code
cargo fmt

# Check Rust code
cargo clippy -- -D warnings

# Lint Python code
uv run ruff check .
uv run ruff format .

# Type check Python code
uv run mypy .

# Build release
uv run maturin develop --release
```
