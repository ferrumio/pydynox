# Dependencies Guidelines

Keep dependencies minimal. Every new dependency adds:
- Compile time (Rust) or install time (Python)
- Binary size
- Security surface
- Maintenance burden

## Rust Dependencies

### Current Core Dependencies

| Crate | Purpose | Why we need it |
|-------|---------|----------------|
| `pyo3` | Python bindings | Required for PyO3 |
| `aws-sdk-dynamodb` | DynamoDB client | Core functionality |
| `aws-sdk-kms` | KMS client | Field encryption |
| `aws-config` | AWS configuration | Credentials, region |
| `tokio` | Async runtime | Required by AWS SDK |
| `serde` + `serde_json` | Serialization | JSON handling |
| `thiserror` | Error types | Clean error definitions |
| `zstd` | Compression | Fast compression |
| `lz4_flex` | Compression | Alternative algorithm |
| `flate2` | Compression | Gzip support |
| `base64` | Encoding | Binary data handling |
| `once_cell` | Lazy statics | One-time initialization |

### Before Adding a Rust Dependency

Ask yourself:

1. **Can I do this with std?** - Rust std library is powerful
2. **Is it maintained?** - Check last commit, open issues
3. **How big is it?** - Check compile time impact
4. **Does it have unsafe code?** - Security concern
5. **Is it widely used?** - More eyes = fewer bugs

### Avoid These

- Crates that pull in half of crates.io
- Crates with no recent activity (>1 year)
- Crates that duplicate what AWS SDK already provides
- Multiple crates for the same thing (pick one compression lib, not five)

## Python Dependencies

### Runtime Dependencies

pydynox has ZERO runtime Python dependencies by default. This is intentional.

The only optional dependency is `pydantic` for the Pydantic integration.

### Why Zero Dependencies?

1. **Faster installs** - Just the wheel, nothing else
2. **No conflicts** - Can't conflict with user's deps
3. **Smaller Lambda** - Important for cold starts
4. **Simpler** - Less can go wrong

### Before Adding a Python Dependency

Think hard. Really hard. Then think again.

If you still want to add one:

1. **Is it optional?** - Put it in `[project.optional-dependencies]`
2. **Is it stable?** - Major version changes break users
3. **Is it small?** - Check transitive dependencies
4. **Is it necessary?** - Can Rust do this instead?

### Dev Dependencies

Dev dependencies are more relaxed. Current ones:

- `pytest` - Testing
- `pytest-asyncio` - Async tests
- `pytest-benchmark` - Performance tests
- `moto` - DynamoDB mocking
- `boto3` - For comparison tests
- `ruff` - Linting
- `mypy` - Type checking

## Adding a New Dependency

### Rust

1. Add to `Cargo.toml` with exact version or range
2. Run `maturin develop` to check compile time impact
3. Document why it's needed in PR

### Python (optional)

1. Add to `[project.optional-dependencies]` in `pyproject.toml`
2. Create a feature flag (like `pydantic`)
3. Document in README how to install

## Version Pinning

### Rust

Use semver ranges:
```toml
pyo3 = "0.27"           # Any 0.27.x
aws-sdk-dynamodb = "1"  # Any 1.x.x
```

### Python

Use minimum versions:
```toml
pydantic = ["pydantic>=2.0"]  # 2.0 or higher
```
