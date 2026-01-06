# Smolagents

Use pydynox with [Smolagents](https://huggingface.co/docs/smolagents) to build AI agents backed by DynamoDB.

## Key features

- Simple `@tool` decorator
- Works with Amazon Bedrock via LiteLLM
- Encrypted fields for sensitive data
- NumberAttribute for calculations

## Getting started

### Installation

```bash
pip install pydynox smolagents litellm
```

## Full example

=== "smolagents_tools.py"
    ```python
    --8<-- "docs/examples/agentic/smolagents_tools.py"
    ```

## Tool patterns

### Working with encrypted data

Encrypted fields are decrypted automatically when read. Don't expose sensitive data in tool responses.

=== "smolagents_encrypted.py"
    ```python
    --8<-- "docs/examples/agentic/smolagents_encrypted.py"
    ```

### Using NumberAttribute

NumberAttribute is great for calculations:

=== "smolagents_numbers.py"
    ```python
    --8<-- "docs/examples/agentic/smolagents_numbers.py"
    ```

### Department queries

=== "smolagents_department.py"
    ```python
    --8<-- "docs/examples/agentic/smolagents_department.py"
    ```

## Tips

### Protect sensitive data

Never return encrypted fields directly. Only return what's needed.

### Validate inputs

Check inputs before database operations.

### Use clear docstrings

Smolagents uses docstrings to understand tools. Write clear descriptions with Args and Returns sections.

## Next steps

- [Strands](strands.md) - AWS agent framework for customer support
- [Pydantic AI](pydantic-ai.md) - Async agent framework with S3 storage
- [Encryption](../encryption.md) - Learn more about field encryption
