# AI Agent Instructions

Welcome! This folder has everything you need to contribute to pydynox.

## Quick Start

1. Read `project-context.md` to understand what pydynox is
2. Read `coding-guidelines.md` before writing code
3. Check `common-mistakes.md` to avoid problems

## Files in This Folder

| File | What it covers |
|------|----------------|
| `project-context.md` | What is pydynox, tech stack, goals |
| `coding-guidelines.md` | Python vs Rust decisions, code style |
| `testing-guidelines.md` | How to write and run tests |
| `dependencies.md` | When to add dependencies |
| `common-mistakes.md` | Things that break the build |
| `writing-style.md` | How to write docs and comments |

## Critical Commands

```bash
# Build the project (NEVER use cargo build)
uv run maturin develop

# Run tests
uv run pytest tests/ -v

# Format code
cargo fmt
uv run ruff check python/ tests/
```

## Project Structure

```
pydynox/
├── src/                    # Rust code
├── python/pydynox/         # Python wrappers
└── tests/                  # All tests (Python)
```

## Need Help?

Open an issue on GitHub if something is unclear.
