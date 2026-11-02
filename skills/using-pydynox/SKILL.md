---
name: using-pydynox
description: Build and test Python applications with pydynox for DynamoDB. Use when application code imports pydynox, or the user asks to use pydynox for models, queries, writes, or application tests.
license: Apache-2.0
metadata:
  author: ferrumio
  version: "1.0"
---

# Using pydynox

Use pydynox's public Python API to build the application's DynamoDB access.
Follow the application's existing table schema, client setup, and async or sync
execution model. The examples need Python 3.11+ with pydynox installed; their
LocalStack mode also needs a running LocalStack instance.

## Check the application first

- Check the project's dependency constraint and installed version, for example
  with `python -c "from importlib.metadata import version; print(version('pydynox'))"`.
  Run this with the application's Python environment.
- The bundled examples use APIs available in pydynox 1.8.0. For another version,
  check its installed signatures or the corresponding release source before
  suggesting an API. Keep the user's dependency choices.
- Identify the table, partition key, optional sort key, and access patterns.
  A model declaration does not create a DynamoDB table.
- Use the application's existing client and AWS credential setup. Configure a
  shared client at startup with `set_default_client`, or pass it in
  `ModelConfig(client=...)` when the model needs a specific client.

## Choose the reference for the task

| Task | Read |
|------|------|
| Client setup, models, attributes, reads, writes, conditions, or sync equivalents | [Models and CRUD](references/models-and-crud.md) |
| Querying, pagination, batch operations, or transactions | [Queries and transactions](references/queries-and-transactions.md) |
| Application tests, memory fixtures, or LocalStack | [Testing](references/testing.md) |

Read the relevant reference as needed. The complete
[application example](examples/application.py) has model definitions and both
async and sync workflows. It can run against the memory backend without AWS.

## API details that matter

- Define models with `ModelConfig(table=...)`. Key attributes use
  `partition_key=True` and `sort_key=True`.
- Operations such as `save`, `get`, `update`, and `delete` are async. Their sync
  versions start with `sync_`.
- `Model.query()` and `Model.scan()` return async iterators: use `async for`.
  `Model.sync_query()` and `Model.sync_scan()` use ordinary `for`.
- `Model.get()` can return `None`. The client-level `get_item()` returns a
  dictionary or `None`, while model methods return model instances.
- Build expressions with attribute operators, such as `Order.pk.not_exists()`.
  Combine conditions with `&` and `|`, with parentheses around comparisons.
- Import exceptions from `pydynox.exceptions`; for example,
  `ConditionalCheckFailedException` for a failed write condition.
- Use public imports from `pydynox`, `pydynox.attributes`, and the documented
  submodules. Check the reference before reaching for an internal module.

For features outside these references, use the
[documentation index](https://ferrumio.github.io/pydynox/llms.txt) to find the
relevant guide. It includes indexes, aliases, Decimal attributes, optimistic
locking, S3, KMS, and Pydantic integration.
