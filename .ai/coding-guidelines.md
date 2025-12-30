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
├── _compression.py      # Internal: compression
├── _encryption.py       # Internal: encryption
└── integrations/        # Pydantic, etc.
```

### Type Hints

Always use type hints:

```python
# Good
def get_item(self, pk: str, sk: Optional[str] = None) -> Optional["Model"]:
    ...

# Bad
def get_item(self, pk, sk=None):
    ...
```

Use `from __future__ import annotations` at the top of files.

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

Order imports like this:

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

## Useful Commands

```bash
# Format Rust code
cargo fmt

# Check Rust code
cargo clippy -- -D warnings

# Lint Python code
uv run ruff check python/ tests/

# Build release
uv run maturin develop --release
```
