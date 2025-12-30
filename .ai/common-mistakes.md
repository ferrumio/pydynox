# Common Mistakes to Avoid

## 1. Using `cargo build`

**Wrong:**
```bash
cargo build
```

**Right:**
```bash
uv run maturin develop
```

This is a PyO3 project. `cargo build` will not produce a usable Python module. Only maturin knows how to build PyO3 bindings correctly.

## 2. Forgetting to Export in `__init__.py`

If you add a new public class or function, you must export it in `__init__.py`. Otherwise users can't import it.

**Wrong:**
```python
# Created new class in model.py but forgot to export
# Users get: ImportError: cannot import name 'NewClass' from 'pydynox'
```

**Right:**
```python
# In __init__.py
from pydynox.model import NewClass

__all__ = [
    # ... existing exports ...
    "NewClass",
]
```

## 3. Using Test Classes

Use plain functions for tests, not classes.

**Wrong:**
```python
class TestUserLogin:
    def test_can_login(self):
        ...
```

**Right:**
```python
def test_user_can_login():
    ...
```

## 4. Missing Type Hints

All Python code needs type hints.

**Wrong:**
```python
def get_item(self, pk, sk=None):
    ...
```

**Right:**
```python
def get_item(self, pk: str, sk: Optional[str] = None) -> Optional["Model"]:
    ...
```

## 5. Missing Doc Comments in Rust

All public Rust items need doc comments.

**Wrong:**
```rust
pub fn serialize(py: Python<'_>, value: PyObject) -> PyResult<PyObject> {
    // ...
}
```

**Right:**
```rust
/// Serialize a Python object to DynamoDB AttributeValue format.
///
/// # Arguments
///
/// * `py` - Python interpreter
/// * `value` - The Python object to serialize
pub fn serialize(py: Python<'_>, value: PyObject) -> PyResult<PyObject> {
    // ...
}
```

## 6. Importing Optional Dependencies at Module Level

Optional dependencies (like Pydantic) must only be imported when used.

**Wrong:**
```python
from pydantic import BaseModel  # Breaks if pydantic not installed

def dynamodb_model(cls):
    ...
```

**Right:**
```python
def dynamodb_model(table: str, hash_key: str):
    try:
        from pydantic import BaseModel
    except ImportError:
        raise ImportError(
            "Pydantic integration requires pydantic. "
            "Install with: pip install pydynox[pydantic]"
        )
```

## 7. Letting AWS SDK Errors Bubble Up

DynamoDB errors must be mapped to our custom exceptions.

**Wrong:**
```rust
let result = self.client.get_item().send().await?;  // Raw SDK error
```

**Right:**
```rust
let result = self.client.get_item().send().await;
match result {
    Ok(output) => { /* ... */ }
    Err(e) => Err(map_sdk_error(e, Some(table)))  // Maps to TableNotFoundError, etc.
}
```

## 8. Putting Hot Path Code in Python

Code that runs on every request should be in Rust.

**Wrong:**
```python
# In Python - runs on every save
def serialize_item(item):
    result = {}
    for key, value in item.items():
        result[key] = convert_to_dynamodb(value)
    return result
```

**Right:**
```rust
// In Rust - fast serialization
pub fn serialize_to_dynamodb(value: &PyAny) -> PyResult<HashMap<String, AttributeValue>> {
    // ...
}
```

## 9. Importing from pydynox_core Directly

Always go through the pydynox module.

**Wrong:**
```python
from pydynox.pydynox_core import serialize
```

**Right:**
```python
from pydynox import pydynox_core
result = pydynox_core.serialize(data)
```

## 10. Not Running Tests Before PR

Always run the full test suite:

```bash
uv run pytest tests/ -v
```

And check formatting:

```bash
cargo fmt
cargo clippy -- -D warnings
uv run ruff check python/ tests/
```
