# Acceptance Criteria

Checklist to run before any PR or commit.

## Why These Checks?

pydynox is a hybrid Rust/Python library. Both sides must work together.

- **Rust core** handles the fast stuff (serialization, compression, DynamoDB calls)
- **Python layer** provides the nice API users interact with
- **PyO3** glues them together

If either side breaks, the whole library breaks. That's why we check both.

The test suite is large (400+ unit tests, 350+ integration tests, 112+ examples) because DynamoDB has many edge cases. We test them all.

## Required Checks

All checks must pass. No exceptions.

### 1. Unit Tests

```bash
uv run pytest tests/unit/ -v
```

All tests must pass.

### 2. Integration Tests

```bash
uv run pytest tests/integration/ -v
```

All tests must pass.

### 3. Examples

```bash
uv run python tests/examples/run_all_examples.py
```

All 112+ examples must pass.

### 4. Python Type Checking

```bash
uv run ty check python/pydynox/ tests/typing/
uv run mypy --strict python/pydynox/
uv run pyright python/pydynox/
```

All three must report zero errors. mypy runs in strict mode; pyright uses its
default mode. Examples are not gated. ty also checks the typing regression files
in `tests/typing/`.

See [the CI workflow](../.github/workflows/ci.yml) for the tool versions and
Python versions used in CI.

### 5. Python Extension Build

```bash
uv run --with maturin maturin develop
```

Must compile without errors.

### 6. Rust Clippy

```bash
cargo clippy
```

No warnings allowed.

### 7. Python Linting

```bash
uv run ruff check .
uv run ruff format --check .
```

Both must pass with zero errors.

## Breaking Changes

No existing test can break unless the issue says "breaking change".

If a test breaks:
1. Check if the issue mentions breaking change
2. If not, fix your code
3. If yes, update the test and document the change

## New Features

When adding new features:

1. Add unit tests in `tests/unit/`
2. Add integration tests in `tests/integration/` if it touches DynamoDB
3. Add example in `tests/examples/` with a descriptive name
4. Update docs if it's a public API change

## Quick Check Script

Run the type checks in section 4 above, then run the remaining checks:

```bash
# Python
uv run ruff check . && uv run ruff format --check .
uv run pytest tests/unit/ -v
uv run pytest tests/integration/ -v
uv run python tests/examples/run_all_examples.py

# Rust
uv run --with maturin maturin develop
cargo clippy
```
