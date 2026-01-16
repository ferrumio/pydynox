# Type Checking

pydynox supports type checkers like mypy. This guide covers how to get the best type checking experience.

## Supported Type Checkers

| Type Checker | Status | Notes |
|--------------|--------|-------|
| mypy | ✅ Tested | Recommended |
| pyright | ✅ Tested | Works well |
| ty (red-knot) | ⚠️ Partial | Descriptors not fully supported yet |

We test with mypy and pyright, but can't guarantee 100% coverage for all edge cases. If you find type issues, please open an issue.

## How It Works

pydynox uses Python descriptors to make attributes work like regular values:

```python
--8<-- "docs/examples/type_checking/basic_types.py"
```

## Attribute Types

Each attribute returns a specific type:

| Attribute | Returns |
|-----------|---------|
| `StringAttribute` | `str` or `None` |
| `NumberAttribute` | `float` or `None` |
| `BooleanAttribute` | `bool` or `None` |
| `BinaryAttribute` | `bytes` or `None` |
| `ListAttribute` | `list[Any]` or `None` |
| `MapAttribute` | `dict[str, Any]` or `None` |
| `StringSetAttribute` | `set[str]` or `None` |
| `NumberSetAttribute` | `set[int or float]` or `None` |
| `JSONAttribute` | `dict[str, Any]` or `list[Any]` or `None` |
| `DatetimeAttribute` | `datetime` or `None` |
| `TTLAttribute` | `datetime` or `None` |
| `CompressedAttribute` | `str` or `None` |
| `EncryptedAttribute` | `str` or `None` |
| `S3Attribute` | `S3Value` or `None` |
| `VersionAttribute` | `int` or `None` |

## CRUD Method Return Types

```python
--8<-- "docs/examples/type_checking/crud_types.py"
```

## Common Issues

### 1. "None" in return types

All attributes can be `None` because:

- The attribute might not be set
- The attribute has `null=True` (default)

If you know a value is not None, use assertion or narrowing:

```python
--8<-- "docs/examples/type_checking/handle_none.py"
```

### 2. Union types from query/scan

`query()` and `scan()` return items that can be `Model` or `dict` because of the `as_dict` parameter. Use `isinstance` to narrow:

```python
for item in User.query(hash_key="USER#1"):
    if isinstance(item, User):
        # mypy knows item is User
        print(item.name)
```

Or if you know you're not using `as_dict=True`:

```python
from typing import cast

for item in User.query(hash_key="USER#1"):
    user = cast(User, item)
    print(user.name)
```

### 3. ty (red-knot) doesn't understand descriptors

ty is a new type checker that doesn't fully support Python descriptors yet. If you see errors like:

```
Object of type `Unknown | str | None` is not assignable to `str`
```

Use mypy or pyright instead. ty will improve over time.

### 4. Pydantic models work out of the box

Pydantic models have native type support:

```python
from pydantic import BaseModel
from pydynox.integrations.pydantic import dynamodb_model

@dynamodb_model(table="products", hash_key="pk")
class Product(BaseModel):
    pk: str
    name: str
    price: float

product = Product(pk="PROD#1", name="Widget", price=9.99)
product.pk    # str (not str | None)
product.name  # str
product.price # float
```

## Best Practices

### 1. Use mypy for type checking

```bash
# Install mypy
pip install mypy

# Run type checking
mypy your_code.py --ignore-missing-imports
```

### 2. Use TYPE_CHECKING for type-only imports

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pydynox.model import ModelQueryResult
```

### 3. Handle None values explicitly

See the examples above for patterns to handle `None` values.

## IDE Support

pydynox includes `py.typed` marker, so IDEs like VS Code and PyCharm will:

- Show correct types on hover
- Autocomplete attribute names
- Warn about type mismatches

Make sure your IDE is configured to use mypy or pyright for type checking.
