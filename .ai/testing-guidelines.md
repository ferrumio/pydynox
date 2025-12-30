# Testing Guidelines

## Test Structure

```
pydynox/tests/
├── python/           # Unit tests (mocked, fast)
│   ├── conftest.py   # Shared fixtures
│   ├── test_model.py
│   ├── test_config.py
│   └── test_hooks.py
└── integration/      # Integration tests (real DynamoDB or moto)
    ├── conftest.py
    ├── hooks/
    └── size/
```

## Running Tests

```bash
uv run pytest                    # All tests
uv run pytest tests/python/      # Unit tests only
uv run pytest tests/integration/ # Integration tests only

# Specific test file
uv run pytest tests/integration/operations/test_get_item.py -v

# Skip benchmarks
uv run pytest tests/ -v --ignore=tests/benchmark
```

Tests use moto server (DynamoDB mock). The conftest.py starts it automatically.

## Why Python Tests?

Tests are written in Python, not Rust. Here's why:

1. **PyO3 bindings need Python** - The Rust code exposes functions to Python. Testing in Rust would only test internal logic, not the actual bindings.

2. **Real usage** - Users call the library from Python. Tests should mirror real usage.

3. **Integration** - Most functions interact with DynamoDB. Python tests can use moto/localstack for mocking.

4. **One test suite** - Easier to maintain one pytest suite than two test systems.

## Test Style

Use plain functions, not classes. Classes add noise without benefit.

### Do This

```python
def test_user_can_login():
    ...

def test_user_cannot_login_with_wrong_password():
    ...
```

### Don't Do This

```python
class TestUserLogin:
    def test_can_login(self):
        ...

    def test_cannot_login_with_wrong_password(self):
        ...
```

## Use pytest.mark.parametrize

When testing the same logic with different inputs:

### Do This

```python
@pytest.mark.parametrize("item", [
    pytest.param({"name": "John", "age": 30}, id="with_age"),
    pytest.param({"name": "Jane", "active": True}, id="with_bool"),
    pytest.param({"name": "Bob", "tags": ["a", "b"]}, id="with_list"),
])
def test_save_item(dynamo, item):
    dynamo.put_item("table", item)
    result = dynamo.get_item("table", {"name": item["name"]})
    assert result == item
```

### Don't Do This

```python
def test_save_item_with_age():
    item = {"name": "John", "age": 30}
    dynamo.put_item("table", item)
    result = dynamo.get_item("table", {"name": "John"})
    assert result == item

def test_save_item_with_bool():
    item = {"name": "Jane", "active": True}
    dynamo.put_item("table", item)
    result = dynamo.get_item("table", {"name": "Jane"})
    assert result == item
```

## Shared Fixtures

Put shared fixtures in `conftest.py`. Don't repeat setup code in each test file.

## Test File Names

Be clear about what the test covers:

- `test_put_get_item.py` - tests for put and get operations
- `test_batch_write.py` - tests for batch write
- `test_query.py` - tests for query operations

## When to Use Rust Tests

Only for pure Rust logic that doesn't touch PyO3:

```rust
// OK to test in Rust - pure logic, no Python
fn calculate_size(data: &[u8]) -> usize {
    data.len()
}

#[cfg(test)]
mod tests {
    #[test]
    fn test_calculate_size() {
        assert_eq!(calculate_size(b"hello"), 5);
    }
}
```

But if the function takes `PyObject` or returns `PyResult`, test it from Python.
