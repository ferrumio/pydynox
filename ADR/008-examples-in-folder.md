# ADR 008: Code examples in separate folder

## Status

Accepted

## Context

Documentation needs code examples. Where should they live?

## Decision

Put all code examples in `docs/examples/` folder, organized by feature.

```
docs/examples/
├── models/
│   ├── basic_model.py
│   └── crud_operations.py
├── query/
│   ├── basic_query.py
│   └── pagination.py
└── ttl/
    ├── basic_ttl.py
    └── session_example.py
```

## Reasons

1. **Linting** - ruff can check examples for errors
2. **Formatting** - ruff can format examples
3. **No duplication** - One source of truth
4. **IDE support** - Full autocomplete when editing
5. **Testable** - Could run examples as smoke tests

## How it works

In markdown, include with snippets:

```markdown
=== "basic_model.py"
    ```python
    --8<-- "docs/examples/models/basic_model.py"
    ```
```

The `--8<--` syntax is from pymdownx.snippets extension.

## Alternatives considered

- **Inline code in markdown** - Can't lint, easy to have errors
- **Doctest** - Limited, hard to show complex examples
- **Jupyter notebooks** - Overkill, hard to version control

## Consequences

- Examples are always valid Python
- Easy to update examples across all docs
- Slightly more complex doc build process
