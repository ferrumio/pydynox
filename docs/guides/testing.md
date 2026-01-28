# Testing

Testing DynamoDB code usually means moto, localstack, or Docker. pydynox has a simpler option: an in-memory backend. No setup, no extra dependencies, just fast tests.

## Why use this?

- **Zero dependencies** - Already included in pydynox. No extra packages to install.
- **No cold start impact** - Only loads when you import it. Your Lambda stays fast.
- **Auto-registered fixtures** - pytest finds them automatically. No conftest.py needed.
- **Fast** - In-memory storage. No network, no Docker.

## Key features

- In-memory backend that mimics DynamoDB
- Auto-registered pytest fixtures
- Seed data support
- Test isolation (each test starts fresh)
- Works with all pydynox operations

## Getting started

### Basic usage

Just add `pydynox_memory_backend` to your test function. That's it.

=== "Async (default)"
    ```python
    --8<-- "docs/examples/testing/basic_fixture.py"
    ```

=== "Sync"
    ```python
    --8<-- "docs/examples/testing/basic_fixture_sync.py"
    ```

The fixture is auto-discovered by pytest. No imports needed, no conftest.py setup.

### How it works

When you use `pydynox_memory_backend`:

1. pydynox switches to an in-memory storage
2. All `save()`, `get()`, `query()`, etc. use this storage
3. After the test, storage is cleared
4. The original client is restored

Each test is isolated. Data from one test doesn't leak to another.

## Fixtures

pydynox provides three fixtures:

| Fixture | Use case |
|---------|----------|
| `pydynox_memory_backend` | Most tests - empty database per test |
| `pydynox_memory_backend_factory` | Tests that need custom seed data |
| `pydynox_memory_backend_seeded` | Tests that share common seed data |

### pydynox_memory_backend

The simplest option. Each test starts with empty tables.

```python
import pytest

@pytest.mark.asyncio
async def test_create_user(pydynox_memory_backend):
    user = User(pk="USER#1", name="John")
    await user.save()
    assert await User.get(pk="USER#1") is not None
```

### pydynox_memory_backend_factory

Use when you need pre-populated data:

=== "seed_data.py"
    ```python
    --8<-- "docs/examples/testing/seed_data.py"
    ```

### pydynox_memory_backend_seeded

For shared seed data across many tests, override `pydynox_seed` in your `conftest.py`:

```python
# conftest.py
import pytest

@pytest.fixture
def pydynox_seed():
    return {
        "users": [
            {"pk": "ADMIN#1", "name": "Admin", "role": "admin"},
            {"pk": "USER#1", "name": "Test User", "role": "user"},
        ]
    }
```

Then use `pydynox_memory_backend_seeded` in your tests:

```python
import pytest

@pytest.mark.asyncio
async def test_admin_exists(pydynox_memory_backend_seeded):
    admin = await User.get(pk="ADMIN#1")
    assert admin.role == "admin"
```

## Inspecting data

Access the backend to inspect stored data:

=== "inspect_data.py"
    ```python
    --8<-- "docs/examples/testing/inspect_data.py"
    ```

## Query and scan

The memory backend supports query and scan with filters:

=== "query_scan.py"
    ```python
    --8<-- "docs/examples/testing/query_scan.py"
    ```

## Testing Lambda handlers

Perfect for testing AWS Lambda functions:

=== "lambda_handler.py"
    ```python
    --8<-- "docs/examples/testing/lambda_handler.py"
    ```

No mocking needed. Your handler code runs exactly as it would in production, just with in-memory storage.

## Without pytest

You can use `MemoryBackend` directly as a context manager or decorator:

=== "context_manager.py"
    ```python
    --8<-- "docs/examples/testing/context_manager.py"
    ```

## Supported operations

The memory backend supports:

| Operation | Supported |
|-----------|-----------|
| `save()` | ✓ |
| `get()` | ✓ |
| `delete()` | ✓ |
| `update()` | ✓ |
| `query()` | ✓ |
| `scan()` | ✓ |
| `batch_write()` | ✓ |
| `batch_get()` | ✓ |
| Conditions | ✓ |
| Atomic updates | ✓ |

!!! note
    Some advanced features like transactions and GSI queries are not yet supported in the memory backend. Use localstack for those cases.

## Comparison with alternatives

| Feature | pydynox fixture | moto | localstack |
|---------|-----------------|------|------------|
| Setup | None | Decorator | Docker |
| Speed | Fastest | Fast | Slow |
| Accuracy | Good | Good | Best |
| Dependencies | None | moto | Docker |
| GSI support | No | Yes | Yes |
| Transactions | No | Yes | Yes |

Use pydynox fixtures for:

- Unit tests
- Fast feedback loops
- CI/CD pipelines
- Simple CRUD tests

Use localstack for:

- Integration tests
- GSI queries
- Transactions
- Full DynamoDB compatibility

## Tips

### Run tests in parallel

The memory backend is isolated per test, so parallel execution works:

```bash
pytest -n auto  # with pytest-xdist
```

### Combine with parametrize

```python
import pytest

@pytest.mark.asyncio
@pytest.mark.parametrize("name,age", [
    ("Alice", 30),
    ("Bob", 25),
    ("Charlie", 35),
])
async def test_create_users(pydynox_memory_backend, name, age):
    user = User(pk=f"USER#{name}", name=name, age=age)
    await user.save()
    
    found = await User.get(pk=f"USER#{name}")
    assert found.age == age
```

### Use autouse for all tests

If you want all tests to use the memory backend:

```python
# conftest.py
import pytest

@pytest.fixture(autouse=True)
def use_memory_backend(pydynox_memory_backend):
    yield
```

Now every test automatically uses in-memory storage.

## Next steps

- [Models](models.md) - Define your data models
- [Query](query.md) - Query items by key
- [Conditions](conditions.md) - Conditional operations
