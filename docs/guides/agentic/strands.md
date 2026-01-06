# Strands Agents

Use pydynox with [Strands Agents](https://github.com/strands-agents/sdk-python) to build AI agents backed by DynamoDB.

## Key features

- Simple `@tool` decorator
- Type-safe tools with docstrings
- Fast DynamoDB operations via pydynox
- Works with Amazon Bedrock models

## Getting started

### Installation

```bash
pip install pydynox strands-agents
```

## Full example

=== "strands_tools.py"
    ```python
    --8<-- "docs/examples/agentic/strands_tools.py"
    ```

## Tool patterns

### CRUD tools

=== "strands_crud.py"
    ```python
    --8<-- "docs/examples/agentic/strands_crud.py"
    ```

## Tips

### Good docstrings matter

Strands uses your docstrings to understand what tools do. Write clear descriptions with Args and Returns sections.

### Handle errors gracefully

Return error info instead of raising exceptions. This lets the agent understand what went wrong and try again.

### Use type hints

Type hints help the agent understand what parameters to pass.

## Next steps

- [Pydantic AI](pydantic-ai.md) - Async agent framework with S3 storage example
- [Smolagents](smolagents.md) - HuggingFace's agent framework with encrypted data
- [Query](../query.md) - Learn more about pydynox queries
