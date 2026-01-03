# ADR 001: Single client.rs file

## Status

Accepted

## Context

The `client.rs` file is large (~1000 lines) and growing. We considered splitting it into multiple files:

```
src/client/
├── mod.rs
├── basic.rs      # get, put, delete, update, query
├── batch.rs      # batch_write, batch_get
├── transaction.rs
├── table.rs
├── partiql.rs
```

## Decision

Keep everything in a single `client.rs` file, organized with section comments.

## Reason

PyO3 does not allow multiple `#[pymethods]` blocks for the same struct across different files without the `multiple-pymethods` feature.

The `multiple-pymethods` feature:
- Adds a dependency on the `inventory` crate
- Adds runtime overhead at startup (method registration)
- Increases binary size

For a library focused on performance, this overhead is not worth the code organization benefit.

## Consequences

- `client.rs` stays as one large file
- Use section comments (`// ========== SECTION ==========`) to organize
- IDE features (folding, outline) help navigate
- No runtime overhead from `inventory` crate
