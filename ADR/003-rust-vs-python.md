# ADR 003: When to use Rust vs Python

## Status

Accepted

## Context

With a hybrid Rust/Python codebase, we need clear rules for where code lives.

## Decision

**Use Rust when:**

- Code runs on every request (serialization, compression)
- Code loops over data (batch processing, transformations)
- Code is CPU-intensive (encryption, compression)
- Code benefits from releasing the GIL

**Use Python when:**

- Code runs once at import time (model definitions, config)
- Code is the public API surface (better IDE support, type hints)
- Code is simple glue between user and Rust
- Code needs to raise user-friendly errors

## How they communicate

```
┌─────────────────────────────────────────────────────────────┐
│                      User Code                              │
│                                                             │
│   user = User(pk="USER#1", name="John")                    │
│   user.save()                                               │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   Python Layer                              │
│                                                             │
│   model.py          - Model class, hooks, validation        │
│   client.py         - DynamoDBClient wrapper                │
│   attributes.py     - Field definitions                     │
│   conditions.py     - Condition builders                    │
│                                                             │
│   Responsibilities:                                         │
│   - Public API with type hints                              │
│   - Run hooks (before_save, after_load)                     │
│   - Build condition expressions                             │
│   - Convert Model to dict                                   │
└─────────────────────────────────────────────────────────────┘
                            │
                            │  pydynox_core.put_item(table, item)
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Rust Layer (PyO3)                        │
│                                                             │
│   client.rs         - DynamoDBClient struct                 │
│   basic_operations/ - get, put, delete, query, partiql      │
│   batch_operations/ - batch_write, batch_get                │
│   serialization.rs  - Python dict ↔ DynamoDB AttributeValue │
│   compression.rs    - zstd, lz4, gzip                       │
│   encryption.rs     - KMS encrypt/decrypt                   │
│                                                             │
│   Responsibilities:                                         │
│   - Serialize Python dict to DynamoDB format                │
│   - Call AWS SDK                                            │
│   - Compress/encrypt data                                   │
│   - Handle retries and errors                               │
│   - Return metrics                                          │
└─────────────────────────────────────────────────────────────┘
                            │
                            │  AWS SDK for Rust
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      DynamoDB                               │
└─────────────────────────────────────────────────────────────┘
```

## Example flow: user.save()

1. **Python**: `Model.save()` runs `before_save` hooks
2. **Python**: `Model.to_dict()` converts model to Python dict
3. **Python**: Calls `pydynox_core.put_item(table, item)`
4. **Rust**: Receives Python dict, converts to `HashMap<String, AttributeValue>`
5. **Rust**: Compresses/encrypts fields if needed
6. **Rust**: Calls AWS SDK `put_item`
7. **Rust**: Returns `OperationMetrics` to Python
8. **Python**: Runs `after_save` hooks

## Examples

| Feature | Python | Rust | Why |
|---------|--------|------|-----|
| Model class definition | ✓ | | Runs once at import |
| Field type definitions | ✓ | | Configuration only |
| Serialize model to DynamoDB | | ✓ | Every save/update |
| Deserialize DynamoDB to model | | ✓ | Every get/query |
| Build condition expressions | | ✓ | String processing |
| Calculate item size | | ✓ | Loops over attributes |
| Compress attributes | | ✓ | CPU-heavy |
| Encrypt fields | | ✓ | CPU-heavy |
| Rate limiting logic | | ✓ | Runs on every request |

## Rule of thumb

If in doubt, put it in Rust. The overhead of crossing the Python-Rust boundary is small compared to the speed gain.

Exception: code that runs once at startup. No point optimizing code that runs once.

## Consequences

- Hot path is fast (Rust)
- Public API has good IDE support (Python)
- Clear separation of concerns
