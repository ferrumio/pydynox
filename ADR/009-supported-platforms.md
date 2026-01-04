# ADR 009: Supported platforms (no Windows)

## Status

Accepted

## Context

pydynox is a PyO3 project that needs pre-built wheels for users to install without compiling Rust.

## Decision

Build wheels for:

- **Linux**: manylinux_2_17 (x86_64, aarch64)
- **macOS**: 11.0+ (x86_64, arm64)

Do not build for:

- **Windows**

## Reasons

### Why manylinux_2_17?

- Compatible with most Linux distros (CentOS 7+, Ubuntu 18.04+, etc.)
- Required glibc version (2.17) is widely available
- AWS Lambda uses Amazon Linux 2 which is compatible
- Older manylinux versions have OpenSSL issues with AWS SDK

### Why macOS 11.0+?

- Supports both Intel and Apple Silicon
- macOS 11 (Big Sur) is the minimum for universal binaries
- Older versions are rare in production

### Why no Windows?

1. **Target audience** - Most DynamoDB users deploy to Linux (Lambda, ECS, EC2)
2. **Maintenance cost** - Windows CI is slower and more complex
3. **Low demand** - No requests for Windows support yet
4. **WSL exists** - Windows developers can use WSL2

If there's demand, Windows support can be added later.

## Build matrix

```yaml
os: [ubuntu-latest, macos-latest]
target:
  - x86_64-unknown-linux-gnu
  - aarch64-unknown-linux-gnu
  - x86_64-apple-darwin
  - aarch64-apple-darwin
```

## Consequences

- Smaller CI matrix (faster builds)
- Less maintenance burden
- Windows users need WSL or can build from source
- Can add Windows later if needed
