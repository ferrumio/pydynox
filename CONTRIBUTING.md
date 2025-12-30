# Contributing to pydynox

Thanks for your interest in pydynox! This guide will help you get started.

## AI-Assisted Contributions

We appreciate GenAI contributions, but we care about quality.

If you're using AI tools to contribute, check the `.ai/` folder:

- `.ai/README.md` - Quick start
- `.ai/project-context.md` - What is pydynox
- `.ai/coding-guidelines.md` - Code style, Python vs Rust
- `.ai/testing-guidelines.md` - How to write tests
- `.ai/common-mistakes.md` - Things to avoid

**Important:** We may close PRs that contain low-quality AI-generated code, code that doesn't make sense, or code without tests. Please review and understand what the AI generated before submitting. We're happy to help if you have questions!

## Setup

### Requirements

- Rust (latest stable)
- Python 3.9+
- maturin

### Install Rust

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

### Clone and Setup

```bash
git clone https://github.com/yourusername/pydyno.git
cd pydyno

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install maturin and dev dependencies
pip install maturin
pip install -e ".[dev]"
```

### Build Locally

```bash
# Build and install in development mode
maturin develop

# Build release version
maturin build --release
```

## Running Tests

### Rust Tests

```bash
cargo test
```

### Python Tests

```bash
# Run all Python tests
pytest

# Run specific test file
pytest tests/python/test_model.py

# Run with verbose output
pytest -v
```

### Property Tests

Property tests use Hypothesis and run many random inputs:

```bash
pytest tests/python/property/
```

### Integration Tests

Integration tests need moto or localstack:

```bash
pytest tests/integration/
```

## Code Style

### Rust

```bash
# Format code
cargo fmt

# Check for issues
cargo clippy
```

### Python

Follow PEP 8. Use type hints everywhere.

```python
# Good
def get_user(user_id: str) -> Optional[User]:
    ...

# Bad
def get_user(user_id):
    ...
```

## Pull Request Process

1. Fork the repo
2. Create a branch: `git checkout -b my-feature`
3. Make your changes
4. Run tests: `cargo test && pytest`
5. Run formatters: `cargo fmt`
6. Push and create a PR

### PR Checklist

- [ ] Tests pass
- [ ] Code is formatted
- [ ] New features have tests
- [ ] Docs updated if API changed

## Project Structure

```
pydyno/
├── src/                    # Rust source code
│   ├── lib.rs             # PyO3 module entry
│   ├── client.rs          # DynamoDB client
│   ├── serialization.rs   # Type conversion
│   └── errors.rs          # Error types
├── python/pydyno/         # Python source code
│   └── __init__.py        # Python API
├── tests/
│   ├── python/            # Python unit tests
│   │   └── property/      # Property-based tests
│   ├── integration/       # Integration tests
│   └── rust/              # Rust test notes
├── Cargo.toml             # Rust dependencies
└── pyproject.toml         # Python config
```

## Questions?

Open an issue on GitHub if you have questions or need help.
