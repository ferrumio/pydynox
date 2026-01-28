# Pydantic AI

Use pydynox with [Pydantic AI](https://ai.pydantic.dev/) to build AI agents backed by DynamoDB.

## Key features

- Type-safe tools with Pydantic validation
- Dependency injection for shared state
- Full async support with pydynox async methods
- S3 storage for large documents
- Works with Amazon Bedrock models

## Getting started

### Installation

```bash
pip install pydynox pydantic-ai
```

## Full example

=== "pydantic_ai_tools.py"
    ```python
    --8<-- "docs/examples/agentic/pydantic_ai_tools.py"
    ```

## Tool patterns

### Async CRUD with S3

=== "pydantic_ai_s3.py"
    ```python
    --8<-- "docs/examples/agentic/pydantic_ai_s3.py"
    ```

### Using dependencies

=== "pydantic_ai_deps.py"
    ```python
    --8<-- "docs/examples/agentic/pydantic_ai_deps.py"
    ```

## Tips

### Use async methods

Pydantic AI is async-first. pydynox is also async-first, so they work great together:

| Async (default) | Sync |
|-----------------|------|
| `await Model.get()` | `Model.sync_get()` |
| `async for x in Model.query()` | `for x in Model.sync_query()` |
| `async for x in Model.scan()` | `for x in Model.sync_scan()` |
| `await model.save()` | `model.sync_save()` |
| `await model.delete()` | `model.sync_delete()` |

### The ctx parameter

Every tool receives a context object as the first parameter. Use it to access dependencies.

### Handle errors

Return error info instead of raising exceptions.

## Next steps

- [Strands](strands.md) - AWS agent framework for customer support
- [Smolagents](smolagents.md) - HuggingFace's agent framework with encrypted data
- [Async](../async.md) - Learn more about async operations
- [S3 attribute](../s3-attribute.md) - Learn more about S3 storage
