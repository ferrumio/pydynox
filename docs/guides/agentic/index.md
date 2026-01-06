# Agentic integrations

Build AI agents with DynamoDB as the data layer. pydynox makes it easy to create tools that agents can use to read and write data.

## Why pydynox for agents?

AI agents need fast, reliable data access. pydynox gives you:

- **Speed** - Rust core means fast serialization and queries
- **Type safety** - Models catch errors before they reach DynamoDB
- **Async support** - Non-blocking operations for async agent frameworks
- **Rich features** - Encryption, S3 storage, compression out of the box

## Use case: Customer support agent

A support agent that can look up customers and orders:

```
User: "What's the status of John's last order?"

Agent:
1. Calls get_customer_by_email("john@example.com") → gets customer_id
2. Calls get_recent_orders(customer_id, limit=1) → gets order
3. Returns: "John's last order (#12345) is 'shipped', tracking: XYZ123"
```

All backed by DynamoDB via pydynox.

## Supported frameworks

| Framework | Best for | Key feature |
|-----------|----------|-------------|
| [Strands](strands.md) | AWS-native apps | Simple `@tool` decorator |
| [Pydantic AI](pydantic-ai.md) | Async apps | Full async support |
| [Smolagents](smolagents.md) | HuggingFace ecosystem | Code generation |

## Quick example

=== "quick_example.py"
    ```python
    --8<-- "docs/examples/agentic/quick_example.py"
    ```

## Feature examples

Each framework guide shows different pydynox features:

| Guide | Features shown |
|-------|----------------|
| [Strands](strands.md) | Queries, NumberAttribute, customer support use case |
| [Pydantic AI](pydantic-ai.md) | S3Attribute, async methods, document management |
| [Smolagents](smolagents.md) | EncryptedAttribute, HR data with sensitive fields |

## Best practices

=== "best_practices.py"
    ```python
    --8<-- "docs/examples/agentic/best_practices.py"
    ```

## Next steps

Pick a framework and get started:

- [Strands](strands.md) - Best for AWS-native applications
- [Pydantic AI](pydantic-ai.md) - Best for async applications
- [Smolagents](smolagents.md) - Best for HuggingFace ecosystem
