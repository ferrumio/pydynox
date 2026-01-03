# ADR 005: Why pytest

## Status

Accepted

## Context

Need a testing framework for Python tests.

## Decision

Use pytest with plain functions (no test classes).

## Reasons

1. **Industry standard** - Most Python projects use pytest
2. **Simple syntax** - Plain functions, no boilerplate
3. **Good fixtures** - Dependency injection for test setup
4. **Parametrize** - Easy to test multiple inputs
5. **Plugins** - pytest-asyncio, pytest-benchmark, etc.

## Style

Use plain functions, not classes:

```python
# Good
def test_user_can_save():
    user = User(pk="USER#1", name="John")
    user.save()
    assert User.get(pk="USER#1") is not None

# Avoid
class TestUser:
    def test_can_save(self):
        ...
```

Use parametrize for multiple inputs:

```python
@pytest.mark.parametrize("value,expected", [
    ("hello", 5),
    ("", 0),
    ("test", 4),
])
def test_string_length(value, expected):
    assert len(value) == expected
```

## Why not unittest?

- More boilerplate (classes, setUp, tearDown)
- Less readable assertions
- No built-in parametrize

## Consequences

- Simple, readable tests
- Easy to add new test cases
- Good async support with pytest-asyncio
