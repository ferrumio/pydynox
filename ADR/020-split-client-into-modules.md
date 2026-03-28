# ADR 020: Split client.rs into domain modules

## Status

Accepted (supersedes [ADR 001](001-single-client-file.md))

## Context

`client.rs` grew to ~1150 lines with ~40 methods in a single `#[pymethods]` block. All methods are pure delegation - they forward arguments to the real implementations in `basic_operations/`, `batch_operations/`, `table_operations/`, and `transaction_operations/`.

ADR 001 decided to keep everything in one file to avoid the `inventory` crate dependency required by PyO3's `multiple-pymethods` feature. At the time, the concerns were:

1. Runtime overhead from method registration
2. Increased binary size
3. Added dependency

Since ADR 001 was written, we re-evaluated these concerns against the current state of the ecosystem and the growing maintenance cost of a 1150-line file.

## Decision

Split `client.rs` into `client/` with domain-grouped modules:

```
src/client/
├── mod.rs              # struct, new, ping, get_region, internal methods
├── basic_ops.rs        # put/get/delete/update (sync + async)
├── query_ops.rs        # query_page, scan_page, count, parallel_scan (sync + async)
├── batch_ops.rs        # batch_write, batch_get (sync + async)
├── transaction_ops.rs  # transact_write, transact_get (sync + async)
├── table_ops.rs        # create/delete/exists/wait table (sync + async)
└── partiql_ops.rs      # execute_statement (sync + async)
```

Each file has its own `#[pymethods]` block. The struct fields changed from private to `pub(crate)` so sub-modules can access them.

## Reasons

**ADR 001's concerns no longer hold:**

- **Runtime overhead is negligible.** The `inventory` crate (v0.3.x) uses a linker-based collection mechanism (`__DATA,__mod_init_func` on macOS, `.init_array` on Linux). Method registration happens once at module import. The measured import time is ~1.8ms total, and every pydynox operation involves a DynamoDB network call (1-100ms). The overhead is unmeasurable in practice.
- **Binary size impact is minimal.** The `inventory` crate is ~200 lines. With LTO and strip enabled in release builds, the difference disappears.
- **The dependency is mature.** `inventory` 0.3.x is widely used in the PyO3 ecosystem and has been stable for years.

**The maintenance cost of the monolithic file grew:**

- Finding and modifying methods requires scrolling through 1150 lines.
- Code review diffs are harder to read when unrelated methods live in the same file.
- New contributors must understand the entire file to add a single operation.
- The section comments (`// ========== SECTION ==========`) were a workaround, not a solution.

## Alternatives considered

**Keep ADR 001 as-is.** The file works, IDE folding helps navigation. But the cost of a single large file compounds as the project grows, while the inventory overhead stays constant.

## Consequences

- `Cargo.toml` adds `multiple-pymethods` to pyo3 features, pulling in `inventory` as a transitive dependency
- Struct fields are `pub(crate)` instead of private (still not visible to Python users)
- `lib.rs` requires no changes - `mod client;` resolves `client/mod.rs` automatically
- All existing `use crate::client::DynamoDBClient` imports keep working
- Python API has zero changes
- ADR 001 is superseded by this decision
