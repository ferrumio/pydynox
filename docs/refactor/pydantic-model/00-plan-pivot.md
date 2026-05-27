# Plan pivot (May 2026)

**Summary**: the original five-PR rollout is superseded. Implementation
starts from upstream `main` with `PydanticModel` as the central deliverable,
not preparatory changes on plain `Model`.

## What changed

In early 2026 the plan was:

1. Rename `ModelConfig` → `DynamoConfig` globally (PR #365).
2. Add `Annotated[T, Dynamo.*]` on plain `Model` (PR #366).
3. Add `cls.F` namespace on both classes.
4. Introduce `PydanticModel`.
5. Deprecate `@dynamodb_model`.

After production-user feedback, the maintainer revised direction in
[issue #364](https://github.com/ferrumio/pydynox/issues/364#issuecomment-4416367765):

### PR #365 — global `DynamoConfig` rename — **not merging**

The rename only existed to free `model_config` for Pydantic's `ConfigDict`.
Since `Model` does **not** inherit from `BaseModel`, there is no naming
collision for existing `Model` users. Renaming would warn every current user
for a problem that does not affect them.

If `PydanticModel` needs a separate config attribute (e.g.
`dynamodb_config: ClassVar[ModelConfig]`), that is handled **inside
`PydanticModel` only**, not via a global rename.

### PR #366 — `Annotated` markers on plain `Model` — **not merging**

The markers are required on `PydanticModel` (Pydantic owns the class body),
but a second declaration style on plain `Model` adds ~840 lines without
helping users who already have explicit `Attribute` descriptors. The
prototype also covered only String/Number/Boolean/Binary, not the complex
types (Map, JSON, List, Enum, Datetime, S3, encrypted, ...) where
`Annotated` actually shines.

Markers ship as part of the `PydanticModel` work with **full attribute type
coverage from day one**, not wired into `ModelMeta` for plain `Model`.

### `cls.F` on plain `Model`

Not rejected in principle, but **deferred**. `User.pk == "x"` stays on plain
`Model` with no deprecation. `cls.F` is implemented on **`PydanticModel`
only**, where Pydantic owns class-level field access.

## New rollout

See [README.md](README.md) for the seven implementation PRs (PRs 1–7 after
this docs PR). The maintainer offered to **pair on metaclass wiring** for
PR 3 (`PydanticModel` core).

## Salvage from closed work

Useful pieces from the closed PR branches may be cherry-picked into the new
sequence:

- Marker → `Attribute` builder logic (into PR 2), without `ModelMeta`
  integration on plain `Model`.
- Internal helper extraction patterns (into PR 1).
- `cls.F` / `AttributeRef` prototype (into PR 4), scoped to
  `PydanticModel`.

Do **not** resubmit PR #365 or #366 as-is.
