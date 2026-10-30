# Type Checking

pydynox ships a `py.typed` marker and full type hints. It works with mypy, pyright, and ty, including their strict modes. This guide shows what types you get and how to set up each checker.

## Supported Type Checkers

| Type Checker | Status | Notes |
|--------------|--------|-------|
| mypy | ✅ Supported | Works with `strict = true` |
| pyright | ✅ Supported | Works with `"typeCheckingMode": "strict"` |
| ty | ✅ Supported | Works with all rules set to `error` |

The examples in this guide pass `mypy --strict`, pyright in strict mode, and ty with all rules set to `error`. They were checked with mypy 2.4.0, pyright 1.1.414, and ty 0.0.64. ty is still in beta, so newer versions may report things differently.

If you find a type issue, please open an issue.

## How It Works

pydynox uses Python descriptors to make attributes work like regular values. On an instance, an attribute returns its value. On the class, it returns the attribute itself, so you can build conditions:

```python
--8<-- "docs/examples/type_checking/basic_types.py"
```

All three checkers understand these descriptors. `user.name` is `str | None`, `User.name` is `StringAttribute`, and `User.name == "John"` is a `ConditionComparison`.

## Attribute Types

Each attribute returns a specific type on an instance:

| Attribute | Returns |
|-----------|---------|
| `StringAttribute` | `str | None` |
| `NumberAttribute` | `float | None` |
| `DecimalAttribute` | `Decimal | None` |
| `BooleanAttribute` | `bool | None` |
| `BinaryAttribute` | `bytes | None` |
| `ListAttribute` | `list[Any] | None` |
| `MapAttribute` | `dict[str, Any] | None` |
| `MapAttribute(MyClass)` | `MyClass | None` |
| `StringSetAttribute` | `set[str] | None` |
| `NumberSetAttribute` | `set[int | float] | None` |
| `JSONAttribute` | `dict[str, Any] | list[Any] | None` |
| `JSONAttribute(MyClass)` | `MyClass | None` |
| `EnumAttribute(MyEnum)` | `MyEnum | None` |
| `DatetimeAttribute` | `datetime | None` |
| `TTLAttribute` | `datetime | None` |
| `CompressedAttribute` | `str | None` |
| `EncryptedAttribute` | `str | None` |
| `S3Attribute` | `S3File | S3Value | None` |
| `VersionAttribute` | `int | None` |
| `VectorAttribute` | `list[float] | None` |

ty shows `float` as `int | float`. This is the same type. A `float` annotation also accepts `int`.

## Handling None

Every attribute is typed `T | None`. This is on purpose. A value can be missing even when you don't expect it:

- The attribute was never set
- The item was loaded with a projection that left it out
- The item was written by other code that skipped it

So `required=True` and `default=...` do not remove `None` from the type. A `StringAttribute(required=True)` is still `str | None`.

Check for `None` before you use the value. All three checkers narrow the type after the check:

```python
--8<-- "docs/examples/type_checking/handle_none.py"
```

After `if user.name is None: raise ...`, the checker knows `user.name` is `str`. Use `or` when a fallback value is fine, like `user.name or ""`.

### S3Attribute values

`S3Attribute` returns the assigned `S3File` until it is uploaded. After upload or loading from DynamoDB, it returns an `S3Value`. An unset attribute returns `None`.

Type checkers cannot infer that `save()` changes the value. Use `isinstance` before reading uploaded metadata:

```python
from pydynox.attributes import S3Value

await doc.save()
uploaded = doc.content
assert isinstance(uploaded, S3Value)
print(uploaded.key)
```

## CRUD Method Return Types

```python
--8<-- "docs/examples/type_checking/crud_types.py"
```

Items from `query()` and `scan()` already have your model type. You don't need `isinstance` or `cast`:

```python
async for user in User.query(partition_key="USER#1"):
    if user.name is not None:
        print(user.name.upper())
```

Pass `as_dict=True` and the items are `dict[str, Any]` instead.

## Strict Configuration

pydynox works with the strict mode of each checker. Here is a config for each one.

### mypy

Add this to your `pyproject.toml`:

```toml
[tool.mypy]
strict = true
```

Then run `mypy .` from your project root.

### pyright

Add a `pyrightconfig.json` to your project root:

```json
{
  "include": ["."],
  "exclude": [".venv"],
  "venvPath": ".",
  "venv": ".venv",
  "pythonVersion": "3.11",
  "typeCheckingMode": "strict"
}
```

`venvPath` and `venv` tell pyright where pydynox is installed. Change them if your virtual environment lives somewhere else. `pythonVersion` sets the Python version to check against. Without it, pyright uses the `python` on your `PATH`, which may be older than 3.11 if the virtual environment is not active. Then run `pyright`.

### ty

ty finds a `.venv` in your project root on its own. To make every rule an error, add this to your `pyproject.toml`:

```toml
[tool.ty.rules]
all = "error"
```

Then run `ty check`.

## Checking Types with reveal_type

Not sure what type the checker sees? Use `reveal_type`:

```python
from typing import reveal_type

user = User(pk="USER#1", name="John")
reveal_type(user.name)
reveal_type(User.name)
```

Each checker prints the type it inferred:

```
mypy:    Revealed type is "str | None"
pyright: Type of "user.name" is "str | None"
ty:      Revealed type: `str | None`
```

For `User.name`, all three show `StringAttribute`. mypy adds the full module path.

`reveal_type` also runs when your code runs. It prints the runtime type, like `Runtime type is 'str'`, so remove it when you're done.

## Pydantic Models

With the Pydantic integration, fields keep their own types, like `str` instead of `str | None`:

```python
from pydantic import BaseModel

from pydynox.integrations.pydantic import dynamodb_model


@dynamodb_model(table="products", partition_key="pk")
class Product(BaseModel):
    pk: str
    name: str
    price: float


product = Product(pk="PROD#1", name="Widget", price=9.99)
```

mypy sees `product.pk` as `str` and `product.price` as `float`.

pyright and ty see the decorated class as `Any`, so they don't check it. If you use pyright or ty and want full type checking, use a `Model` subclass instead.

## IDE Support

Because pydynox includes `py.typed`, editors that use a type checker will:

- Show correct types on hover
- Autocomplete attribute names
- Warn about type mismatches

VS Code with Pylance uses pyright.
