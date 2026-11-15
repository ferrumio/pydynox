# ADR 021: Optional Pydantic integration via `PydanticModel`

## Status

Proposed (revised May 2026 after maintainer feedback on
[issue #364](https://github.com/ferrumio/pydynox/issues/364); Pydantic stays
optional and plain `Model` is not changed).

## Context

pydynox currently offers two overlapping ways to declare a DynamoDB-backed
model:

1. The **`Model` class** in [python/pydynox/model.py](../python/pydynox/model.py)
   with `Attribute` descriptors in [python/pydynox/attributes/](../python/pydynox/attributes/).
   Full DynamoDB feature set (GSI/LSI, templates, aliases, encryption, TTL,
   version, S3 offload, discriminator, hooks, auto-generate, dirty tracking,
   transactions, batch). No Pydantic-level features: no `Field(description=...)`,
   no validators, no JSON schema, no `model_dump_json()`.

2. The **`@dynamodb_model` decorator** in
   [python/pydynox/integrations/pydantic.py](../python/pydynox/integrations/pydantic.py).
   Wraps an arbitrary `BaseModel` and adds `save`/`get`/`delete`/`update` only.
   Loses almost every pydynox DynamoDB feature listed above.

Users who want both a rich Pydantic schema (descriptions, validators,
constraints, JSON schema) and pydynox's DynamoDB features today have no path.

### Constraint: Pydantic must remain optional

pydynox's core value is speed and a minimal dependency footprint. The Rust
core handles serialization, compression, encryption, and all AWS SDK calls.
Making Pydantic a required runtime dependency goes against that principle.
Pydantic is installed today via the `pydynox[pydantic]` extra and must stay
optional.

This rules out evolving `Model` into a `pydantic.BaseModel` subclass, which
would force every user to depend on Pydantic.

### Plan pivot (May 2026)

An earlier rollout proposed preparatory PRs: global `ModelConfig` rename,
`Annotated` markers on plain `Model`, and `cls.F` on both classes. After
production-user feedback, the maintainer closed
[PR #365](https://github.com/ferrumio/pydynox/pull/365) and
[PR #366](https://github.com/ferrumio/pydynox/pull/366) and directed work
toward **`PydanticModel` first**, with markers and config naming scoped to
that class. See
[docs/refactor/pydantic-model/00-plan-pivot.md](../docs/refactor/pydantic-model/00-plan-pivot.md).

## Decision

Introduce a new, **opt-in** `PydanticModel` class that inherits from both
`Model` and `pydantic.BaseModel`:

```python
from pydynox import Model          # no Pydantic; works exactly as today
from pydynox import PydanticModel  # Model + BaseModel; requires pydynox[pydantic]
```

`PydanticModel` lives in a new module
[python/pydynox/pydantic_model.py](../python/pydynox/pydantic_model.py) and is
lazily imported: a user without Pydantic installed can still
`import pydynox` and use `Model` as today; only `from pydynox import
PydanticModel` triggers the import and raises a clear `ImportError` with a
pointer to `pip install pydynox[pydantic]` if Pydantic is missing.

Supporting changes, scoped to **`PydanticModel` only** (plain `Model` unchanged):

- **`Annotated[T, Dynamo.*]` markers** with full attribute-type coverage,
  consumed by `_collect_dynamodb_schema` from Pydantic `FieldInfo.metadata`.
  Not wired into `ModelMeta` for plain `Model`. See
  [02-dynamo-markers.md](../docs/refactor/pydantic-model/02-dynamo-markers.md).
- **`dynamodb_config: ClassVar[ModelConfig]`** on `PydanticModel` subclasses
  so Pydantic's `model_config = ConfigDict(...)` remains available. Plain
  `Model` keeps `model_config = ModelConfig(...)` with no rename.
- **`cls.F` namespace** for conditions and atomic ops on `PydanticModel`
  because Pydantic owns class-level field access. Plain `Model` keeps
  `User.pk == "x"` with no deprecation. See
  [04-fields-namespace.md](../docs/refactor/pydantic-model/04-fields-namespace.md).
- **Deprecate `@dynamodb_model`** and point users at `PydanticModel`. See
  [07-deprecate-decorator.md](../docs/refactor/pydantic-model/07-deprecate-decorator.md).

Implementation rolls out in seven small PRs documented in
[docs/refactor/pydantic-model/README.md](../docs/refactor/pydantic-model/README.md).

## Reasons

- **Zero impact on non-Pydantic users.** No global renames, no second field
  declaration style on plain `Model`, no new required dependencies.
- **Single codebase for the DynamoDB feature set.** `PydanticModel`
  inherits from `Model`, so GSI/LSI, transactions, batch, hooks, metrics,
  `create_table`, atomic ops, version, TTL, encryption, compression, S3
  offload, discriminator, and auto-generate are all shared.
- **No breaking changes.** All PRs ship on minor versions.
- **Clean deprecation path for `@dynamodb_model`.** Users migrate to
  `PydanticModel` and gain the full DynamoDB feature set at the same time.

## Alternatives considered

- **Make `Model` a `BaseModel` directly**: rejected. Forces Pydantic as a
  required dependency and breaks every existing user.
- **Global `ModelConfig` → `DynamoConfig` rename**: rejected (PR #365).
  Warns all `Model` users for a collision that only affects `PydanticModel`.
- **`Annotated` markers on plain `Model`**: rejected (PR #366). Second
  declaration style without benefit to descriptor users; incomplete type
  coverage in the prototype.
- **Leave the two worlds as-is**: rejected. The decorator path keeps
  accumulating feature gaps.
- **Extend the decorator to feature parity**: rejected. Two parallel
  implementations of the same `Attribute` pipeline.

## Consequences

Positive:

- Plain `Model` users see no change.
- `PydanticModel` users get Pydantic features **and** every pydynox DynamoDB
  feature via inheritance.
- One class to maintain for DynamoDB logic; `PydanticModel` is a thin layer.

Negative / trade-offs:

- Two public model base classes. Documentation must explain when to pick which.
- `PydanticModel` users must use `Annotated[...]` and `cls.F` — Pydantic
  constraints, not pydynox's preference.
- `__setattr__`-based dirty tracking must cooperate with
  `validate_assignment` on `PydanticModel`.

## References

- [docs/refactor/pydantic-model/overview.md](../docs/refactor/pydantic-model/overview.md)
- [docs/refactor/pydantic-model/00-plan-pivot.md](../docs/refactor/pydantic-model/00-plan-pivot.md)
- [issue #364](https://github.com/ferrumio/pydynox/issues/364#issuecomment-4416367765)
- PR specs: [01](../docs/refactor/pydantic-model/01-extract-schema-collection.md) –
  [07](../docs/refactor/pydantic-model/07-deprecate-decorator.md)
