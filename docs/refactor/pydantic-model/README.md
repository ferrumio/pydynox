# Optional Pydantic integration refactor

This folder collects the planning documents for giving pydynox users an
**opt-in** path to Pydantic features (`Field(description=...)`, validators,
JSON schema, `model_dump_json()`, ...) without changing the existing
`Model` class and without forcing Pydantic as a required dependency.

The refactor introduces a new `PydanticModel(Model, BaseModel)` sibling
class. `Model` itself stays exactly as today. Pydantic stays behind the
`pydynox[pydantic]` extra.

## Status

**Revised May 2026** after maintainer feedback on
[issue #364](https://github.com/ferrumio/pydynox/issues/364). The original
five-PR plan (global `DynamoConfig` rename, `Annotated` markers on plain
`Model`, then `PydanticModel`) is superseded. See
[00-plan-pivot.md](00-plan-pivot.md).

Proposed. See [ADR 021](../../../ADR/021-pydantic-base-model.md).

## Reading order

1. **[overview.md](overview.md)** — motivation, architecture, rollout,
   risks.
2. **[00-plan-pivot.md](00-plan-pivot.md)** — why the plan changed; what
   happened to closed PRs #365 and #366.
3. **[01-extract-schema-collection.md](01-extract-schema-collection.md)** —
   PR 1: internal refactor; extract helpers from `ModelMeta`.
4. **[02-dynamo-markers.md](02-dynamo-markers.md)** — PR 2: full
   `Annotated[T, Dynamo.*]` marker library for `PydanticModel` only.
5. **[03-pydantic-model-core.md](03-pydantic-model-core.md)** — PR 3:
   `PydanticModel` + combined metaclass + basic CRUD (pair with maintainer).
6. **[04-fields-namespace.md](04-fields-namespace.md)** — PR 4: `cls.F`
   on `PydanticModel` for conditions and atomic ops.
7. **[05-lifecycle-shims.md](05-lifecycle-shims.md)** — PR 5: dirty
   tracking, `to_dict`/`from_dict`, auto-generate hooks.
8. **[06-parity-tests.md](06-parity-tests.md)** — PR 6: feature parity
   matrix and gap fixes.
9. **[07-deprecate-decorator.md](07-deprecate-decorator.md)** — PR 7:
   deprecate `@dynamodb_model` and point users at `PydanticModel`.

## At a glance

| PR | Title | Breaking? | Size | Touches plain `Model`? |
|----|-------|-----------|------|------------------------|
| 0  | Revise plan docs (this PR) | no | S | no |
| 1  | Extract schema collection helpers | no | S | internal only |
| 2  | `Dynamo.*` markers (Pydantic path) | no | M | no |
| 3  | `PydanticModel` core + metaclass | no | L | no (new class) |
| 4  | `cls.F` namespace | no | M | no |
| 5  | Lifecycle shims | no | M | no |
| 6  | Parity tests | no | M–L | no |
| 7  | Deprecate `@dynamodb_model` | no | S–M | warnings only |

Every implementation PR ships on a minor version. No major-version bump
required.

## Conventions for these docs

Each PR document uses the same sections:

- **Title** + one-line summary
- **Motivation**
- **Scope** (in / out)
- **Files touched**
- **Public API changes** (before / after)
- **Back-compat + deprecation notes**
- **Test plan**
- **Size estimate**
- **Depends on / unblocks**
