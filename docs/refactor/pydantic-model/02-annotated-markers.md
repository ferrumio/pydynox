# PR 2: `Annotated` + `Dynamo.*` field markers (implemented)

## Summary

Adds optional [PEP 593](https://peps.python.org/pep-0593/) `typing.Annotated` metadata
(`Dynamo.String`, `Dynamo.Number`, `Dynamo.Boolean`, `Dynamo.Binary`) so model fields
can be declared in a type-checker–friendly way while the metaclass still builds
the same :class:`pydynox.attributes.Attribute` instances as the legacy
``pk = StringAttribute(...)`` style.

- **Non-breaking:** class-body attribute descriptors are unchanged; if both an
  annotation and a descriptor are present for a name, the **descriptor wins**.
- **Narrow resolvers only:** the implementation resolves `__annotations__` for the
  current class only (not `typing.get_type_hints` on the full MRO), to avoid
  evaluating forward references from base `Model` members during metaclass
  execution.
- **Future Pydantic path:** this syntax is the intended bridge toward an optional
  `PydanticModel` (see ADR 021) without a naming collision on `model_config`.


## Scope shipped

| Marker            | Python type | Attribute class        |
|-------------------|------------|-------------------------|
| `Dynamo.String`   | `str`      | `StringAttribute`       |
| `Dynamo.Number`   | `int`/`float` | `NumberAttribute`    |
| `Dynamo.Boolean`  | `bool`     | `BooleanAttribute`      |
| `Dynamo.Binary`   | `bytes`    | `BinaryAttribute`       |

Further attribute kinds (list, map, JSON, encrypted, etc.) can follow the same
pattern in a later change.

## References

- [`python/pydynox/dynamo.py`](../../../python/pydynox/dynamo.py) — public markers
- [`python/pydynox/_internal/_dynamo_annotated.py`](../../../python/pydynox/_internal/_dynamo_annotated.py) — synthesis
- :class:`pydynox._internal._model._base.ModelMeta` — metaclass hook
