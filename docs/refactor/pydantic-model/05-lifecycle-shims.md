# PR 5: Lifecycle shims on `PydanticModel`

**Summary**: implement dirty tracking that cooperates with Pydantic
`validate_assignment`, plus `to_dict` / `from_dict` shims and
auto-generate / template key hooks via `@model_validator`.

## Motivation

`ModelBase` tracks changes via `_original` and `_changed_fields` in
`__setattr__`. Pydantic's `validate_assignment=True` must run first so invalid
assignments raise `ValidationError` without polluting dirty state.

CRUD, transactions, and batch call `to_dict` / `from_dict` today. Keeping
those names on `PydanticModel` preserves call-site compatibility while
internally delegating to `model_dump` / `model_validate` plus
`Attribute.serialize` / `deserialize` for custom wire formats.

## Scope

In:

- `PydanticModel.__setattr__`:
  1. Delegate to `BaseModel.__setattr__` (validation).
  2. On success, update `_original` / `_changed_fields` like `ModelBase`.
- `to_dict(self, *, for_dynamo: bool = True)`:
  1. `model_dump(mode="python", by_alias=True)`.
  2. Apply `Attribute.serialize` where needed (encryption, S3, datetime, ...).
  3. Merge templated partition/sort keys via `_build_template_keys`.
- `from_dict(cls, data)`:
  1. Apply `Attribute.deserialize`.
  2. `cls.model_validate(...)`.
- `@model_validator(mode="after")` calling `_apply_auto_generate()` and
  template key preparation where appropriate.

Out:

- Changing `ModelBase` dirty tracking on plain `Model`.
- Removing `to_dict` / `from_dict` from plain `Model`.

## `__setattr__` sketch

```python
def __setattr__(self, name: str, value: object) -> None:
    had_value = name in self.__dict__
    old = self.__dict__.get(name)
    super().__setattr__(name, value)  # BaseModel: validates if enabled
    attr = type(self)._attributes.get(name)
    if attr is not None and (not had_value or old != self.__dict__[name]):
        self._changed_fields.add(name)
        self._original.setdefault(name, old)
```

## Test plan

- Invalid assignment raises `ValidationError`; `_changed_fields` unchanged.
- Valid assignment updates dirty state once.
- `to_dict` / `from_dict` round-trip matches `Model` wire format for same data.
- AutoGenerate + template keys produce correct partition key on `save()`.
- `is_dirty` / `changed_fields` / skip-save-when-clean behavior.

## Size

M. Roughly 150–250 LOC + tests.

## Depends on / unblocks

- Depends on: PR 3.
- Unblocks: PR 6 (parity relies on correct serialization path).
