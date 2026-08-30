# PR 7: Deprecate `@dynamodb_model` and consolidate docs

**Summary**: now that `PydanticModel` reaches feature parity, the
`@dynamodb_model` decorator is redundant. Add `DeprecationWarning`, update
docs/examples, and publish a migration guide. Do **not** remove the decorator.

## Motivation

Before `PydanticModel`, the decorator was the only Pydantic path — at the cost
of almost every DynamoDB feature. After PRs 3–6 that trade-off is gone.
Keeping two Pydantic integration paths splits documentation and maintenance.

## Scope

In:

- `DeprecationWarning` at decorator call time in:
  - [python/pydynox/integrations/pydantic.py](../../../python/pydynox/integrations/pydantic.py)
  - [python/pydynox/integrations/functions.py](../../../python/pydynox/integrations/functions.py)
- Docstring deprecation notes on integration modules.
- Migration guide: "Migrating from `@dynamodb_model` to `PydanticModel`".
- Update [docs/guides/pydantic.md](../../../docs/guides/pydantic.md),
  getting-started examples, README headline example where applicable.
- Paired equivalence test: decorator model vs `PydanticModel` with equivalent
  fields produces equivalent save/get behavior.
- [CHANGELOG.md](../../../CHANGELOG.md) entry.

Out:

- Removing `@dynamodb_model` (future major).
- Deprecating `JSONAttribute[M]` on plain `Model`.
- Any change to plain `Model` API.

## Warning message (sketch)

```text
@dynamodb_model is deprecated; subclass pydynox.PydanticModel instead.
See docs/guides/pydantic.md#migrating-from-dynamodb_model
```

## Back-compat

Decorator continues to work; warnings only.

## Test plan

- Warning emitted once per decorator application (or documented policy).
- Existing decorator integration tests still pass.
- Migration equivalence test from PR 6 scope.

## Size

S–M. Roughly 100–200 LOC code + docs.

## Depends on / unblocks

- Depends on: PR 6 (parity proven).
- Unblocks: future major removal of decorator (not scheduled).
