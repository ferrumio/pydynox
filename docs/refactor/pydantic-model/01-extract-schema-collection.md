# PR 1: Extract schema collection helpers

**Summary**: factor index, hook, and discriminator collection out of
`ModelMeta.__new__` into reusable helpers. Zero user-visible change on
`Model`; enables `PydanticModel` metaclass to populate the same class
dunders without duplicating logic.

## Motivation

`ModelMeta.__new__` today scans the class body for `Attribute` descriptors,
GSI/LSI declarations, hook methods, and discriminator metadata, then
populates `_attributes`, `_indexes`, `_hooks`, and related dunders.

`PydanticModel` (PR 3) will populate those same dunders from Pydantic
`model_fields` instead of class-body descriptors, but still needs identical
index/hook/discriminator handling. Extracting shared helpers first keeps PR 3
focused on metaclass cooperation rather than copy-paste.

## Scope

In:

- New helpers in
  [python/pydynox/_internal/_model/_base.py](../../../python/pydynox/_internal/_model/_base.py)
  (or a sibling module), e.g.:
  - `_collect_indexes(namespace, bases) -> (indexes, local_indexes)`
  - `_collect_hooks(namespace, bases) -> hooks`
  - `_collect_discriminator(attributes) -> (discriminator_attr, registry)`
  - `_finalize_schema(cls, attributes, ...) -> None` (populate dunders)
- `ModelMeta.__new__` calls the helpers; behavior unchanged.

Out:

- Any new public API.
- `PydanticModel`, markers, or `cls.F`.
- Changing how attributes are discovered on plain `Model`.

## Files touched

- [python/pydynox/_internal/_model/_base.py](../../../python/pydynox/_internal/_model/_base.py)
- Existing `Model` unit/integration tests (must pass unchanged).

## Public API changes

None.

## Back-compat

Identical `Model` behavior. No deprecations.

## Test plan

- Full existing test suite green.
- Optional: add a narrow unit test asserting helper outputs match pre-refactor
  dunders for a fixture model with GSI, LSI, hooks, and discriminator.

## Size

S. Roughly 80–150 LOC moved/refactored.

## Depends on / unblocks

- Depends on: nothing (first implementation PR after docs).
- Unblocks: PR 3 (`PydanticModel` metaclass reuses helpers).
