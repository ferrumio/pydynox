# PR 6: Feature parity tests

**Summary**: expand the test matrix so every pydynox DynamoDB feature works
on `PydanticModel` with byte-identical wire format and equivalent behavior
to plain `Model`. Fix gaps discovered in the `PydanticModel` path only.

## Motivation

PR 3 proves a vertical slice. Production confidence requires parity across
the full feature surface: indexes, transactions, security attributes, hooks,
discriminator, TTL, version conflicts, and more.

This PR is primarily tests plus targeted fixes in
`pydantic_model.py` / marker builder — not changes to plain `Model` or shared
CRUD modules unless a genuine bug is found.

## Scope

In:

- New test directory e.g.
  [tests/unit/pydantic_model/](../../../tests/unit/pydantic_model/) or
  [tests/integration/pydantic_model/](../../../tests/integration/pydantic_model/).
- Parity fixtures: paired `Model` and `PydanticModel` classes with equivalent
  declarations for each scenario.
- Scenarios (minimum):

| Area | Scenarios |
|------|-----------|
| Keys | partition, sort, composite templates, aliases |
| Indexes | GSI query, LSI query, INCLUDE projection |
| Transactions | put, update, delete, condition_check |
| Batch | batch read / write |
| Hooks | `@before_save`, `@after_get`, ... |
| Conditions / atomics | via `cls.F` (PR 4) |
| Discriminator | polymorphic read/write |
| TTL / Version | expiry, optimistic locking conflict |
| Secure attrs | encrypted, compressed, S3 offload |
| AutoGenerate | ULID, UUID4, created_at, updated_at |
| Dirty tracking | `is_dirty`, changed_fields, clean save skip |

- Pydantic-specific tests:
  - `Field(description=...)` in `model_json_schema()`.
  - `@field_validator` rejects bad input on `save()`.
  - Nested `BaseModel` round-trip.
  - `validate_assignment` + dirty tracking (PR 5).

Out:

- New features not already supported on `Model`.
- Parity work on plain `Model` (regression bar only).

## Splitting

If review size is too large, split into stacked PRs:

- `test/pydantic-model-parity-keys-indexes`
- `test/pydantic-model-parity-tx-batch`
- `test/pydantic-model-parity-secure-hooks`

Each must keep the full suite green.

## Size

M–L. Roughly 400–800 LOC tests; fixes as needed.

## Depends on / unblocks

- Depends on: PRs 3, 4, 5 (minimum 3; 4–5 for full matrix).
- Unblocks: PR 7 (migration equivalence test).
