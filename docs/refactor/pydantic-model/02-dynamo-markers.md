# PR 2: `Dynamo.*` markers (Pydantic path only)

**Summary**: add a `pydynox.Dynamo` namespace of frozen metadata markers and
an `attribute_from_annotated()` builder that synthesizes existing
`Attribute` subclasses from `Annotated[T, Dynamo.*]`. Used by
`PydanticModel` only — **not** wired into `ModelMeta` for plain `Model`.

## Motivation

`PydanticModel` cannot use class-body `Attribute` descriptors; Pydantic owns
class-body assignments. PEP 593 `Annotated[T, ...]` is the canonical way to
attach pydynox metadata while preserving the underlying type for Pydantic and
type checkers.

Closed PR #366 proved the builder pattern but was rejected because it (a)
depended on a global config rename, (b) only covered four primitive types, and
(c) added a second declaration style on plain `Model` that did not help
existing users. This PR delivers **full attribute coverage** and keeps the
markers **private to the Pydantic path** until PR 3 wires them in.

## Scope

In:

- New module [python/pydynox/dynamo.py](../../../python/pydynox/dynamo.py)
  (or `markers.py`) exporting `Dynamo` as a namespace of frozen dataclasses.
- Internal builder
  [python/pydynox/_internal/_dynamo_annotated.py](../../../python/pydynox/_internal/_dynamo_annotated.py)
  with `attribute_from_annotated(name, annotation) -> Attribute`.
- Full marker inventory (see table below).
- Unit tests per marker and type-inference rule.
- Export `Dynamo` from `pydynox` (markers are harmless without `PydanticModel`).

Out:

- `ModelMeta` scanning `__annotations__` on plain `Model`.
- `PydanticModel` class itself (PR 3).
- Global `ModelConfig` → `DynamoConfig` rename.

## Marker inventory

| Marker | Maps to | Key parameters |
|--------|---------|----------------|
| `Dynamo.partition_key` | `partition_key=True` | `template`, `alias` |
| `Dynamo.sort_key` | `sort_key=True` | `template`, `alias` |
| `Dynamo.alias` | DynamoDB attribute name | `name` |
| `Dynamo.template` | template on non-key field | `template` |
| `Dynamo.auto_gen` | `AutoGenerate` default | `strategy` |
| `Dynamo.required` | `required=True` | — |
| `Dynamo.discriminator` | `discriminator=True` | — |
| `Dynamo.ttl` | `TTLAttribute` | `ttl_seconds` |
| `Dynamo.version` | `VersionAttribute` | — |
| `Dynamo.encrypted` | `EncryptedAttribute` | `key_id`, `mode`, ... |
| `Dynamo.compressed` | `CompressedAttribute` | `algorithm`, `level` |
| `Dynamo.s3` | `S3Attribute` | `bucket`, `key_prefix`, ... |
| `Dynamo.json` | `JSONAttribute` | optional typed model |
| `Dynamo.enum` | `EnumAttribute` | `enum` type |
| `Dynamo.datetime` | `DatetimeAttribute` | `format` |
| `Dynamo.string_set` | `StringSetAttribute` | — |
| `Dynamo.number_set` | `NumberSetAttribute` | — |

Multiple markers combine on one field:
`Annotated[str, Dynamo.partition_key(), Dynamo.alias("PK")]`.

## Type inference

When no explicit type marker is present, infer `Attribute` subclass from `T`:

- `str` → `StringAttribute`
- `int` / `float` → `NumberAttribute`
- `bool` → `BooleanAttribute`
- `bytes` → `BinaryAttribute`
- `list[...]` → `ListAttribute`
- `dict[str, ...]` → `MapAttribute`
- `set[str]` → `StringSetAttribute`
- `set[int|float]` → `NumberSetAttribute`
- `Enum` subclass → `EnumAttribute`
- `datetime` → `DatetimeAttribute`
- `BaseModel` subclass → `JSONAttribute[That]`

Unknown types raise `TypeError` at build time with a pointer to these docs.

## Public API

```python
from typing import Annotated
from pydynox import Dynamo

pk: Annotated[str, Dynamo.partition_key(template="USER#{user_id}")]
```

Markers are inert until PR 3 connects them to `PydanticModel`.

## Back-compat

Plain `Model` unchanged. No new declaration path on `Model`.

## Test plan

- Unit test each marker → correct `Attribute` subclass and kwargs.
- Combined markers (partition key + alias + auto_gen).
- Type inference for every row in the inference table.
- Negative cases: unknown type, conflicting markers.

## Size

M. Roughly 300–500 LOC including tests.

## Depends on / unblocks

- Depends on: PR 1 (optional; can land in parallel).
- Unblocks: PR 3 (`_collect_dynamodb_schema` reads markers).
