# ADR 002: Why Rust

## Status

Accepted

## Context

pydynox needs to be fast. DynamoDB operations involve serialization, compression, encryption, and data transformation on every request.

## Decision

Use Rust for the performance-critical core, exposed to Python via PyO3.

## Reasons

1. **Speed** - Rust is as fast as C but memory-safe. Serialization in Rust is 10-50x faster than pure Python.

2. **No GIL** - Rust code releases Python's GIL during CPU work. This means real parallelism.

3. **AWS SDK** - The official AWS SDK for Rust is mature and well-maintained.

4. **PyO3** - Excellent Python bindings. The Rust code feels native to Python users.

5. **Single binary** - Users install a wheel. No need to compile anything or install Rust.

## Alternatives considered

- **Pure Python with boto3** - Too slow for the performance goals
- **Cython** - Still limited by Python's data structures
- **C extension** - Memory safety concerns, harder to maintain

## Consequences

- Faster serialization, compression, and encryption
- More complex build process (maturin)
- Contributors need to know Rust for core changes
- Smaller binary than pure Python (no boto3 dependency)
