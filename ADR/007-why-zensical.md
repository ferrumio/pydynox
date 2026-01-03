# ADR 007: Why Zensical for docs

## Status

Accepted

## Context

Need a documentation system that supports code examples, tabs, and looks good.

## Decision

Use Zensical (MkDocs Material wrapper) with `zensical.toml` config.

## Reasons

1. **MkDocs Material** - Beautiful, modern documentation theme
2. **Single config file** - `zensical.toml` instead of `mkdocs.yml`
3. **Code snippets** - Include code from external files with `--8<--`
4. **Tabs** - Show multiple examples side by side
5. **Admonitions** - Tips, warnings, notes
6. **Search** - Built-in full-text search

## Code examples in separate files

Examples live in `docs/examples/` and are included via snippets:

```markdown
=== "basic_model.py"
    ```python
    --8<-- "docs/examples/models/basic_model.py"
    ```
```

Benefits:
- Examples can be linted with ruff
- Examples can be type-checked
- No copy-paste errors between docs and code
- IDE support when editing examples

## Alternatives considered

- **Sphinx** - More complex, RST syntax
- **Plain MkDocs** - Less features than Material
- **Docusaurus** - JavaScript-based, overkill for Python project

## Consequences

- Beautiful documentation
- Examples are always valid Python
- Easy to maintain
