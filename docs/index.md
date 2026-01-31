# pydynox

An async-first DynamoDB ORM for Python with a Rust core.

!!! info "📢 Stable Release: March 2-6, 2026"
    We're in the final stretch! The API is stabilizing, performance is being polished, and we're building the remaining features. We might release earlier if everything goes well. Stay tuned!

## The problem

DynamoDB's API is verbose. Every value needs a type annotation:

```python
# boto3
response = table.put_item(Item={
    'pk': {'S': 'USER#123'},
    'name': {'S': 'John'},
    'age': {'N': '30'},
    'tags': {'L': [{'S': 'admin'}, {'S': 'active'}]}
})
```

This gets old fast. You write the same boilerplate for every operation, and typos in type annotations (`'S'` vs `'N'`) cause runtime errors.

## The solution

pydynox gives you a Pythonic API:

```python
# pydynox
user = User(pk="USER#123", name="John", age=30, tags=["admin", "active"])
await user.save()
```

You define models with typed attributes. pydynox handles serialization, validation, and all the DynamoDB quirks.

## Why Rust?

The slow part of any ORM is serialization - converting Python objects to DynamoDB format and back. Pure Python ORMs do this with loops and dictionary operations, which is slow.

pydynox does serialization in Rust. Even for a single item, you get faster serialization and the GIL is released during network calls. For batch operations with thousands of items, the difference is 10-50x.

## GIL-free async

Python has a Global Interpreter Lock (GIL). Only one thread runs Python code at a time. When you call `await` on a network operation, Python should be free to run other coroutines. But if the library holds the GIL while waiting, nothing else can run.

pydynox releases the GIL before making network calls. The Rust core uses [tokio](https://tokio.rs/) (an async runtime for Rust) to handle the actual HTTP requests. When you `await` a pydynox operation, PyO3's [`future_into_py`](https://docs.rs/pyo3/latest/pyo3/coroutine/fn.future_into_py.html) bridges Python's asyncio with tokio, and the GIL is released during the entire network call.

```
Python                    Rust (tokio)              DynamoDB
  |                         |                          |
  |-- await user.save() --->|                          |
  |   (GIL released)        |-- HTTP request --------->|
  |                         |                          |
  |   (other coroutines     |   (waiting)              |
  |    can run here)        |                          |
  |                         |<-- HTTP response --------|
  |<-- result --------------|                          |
  |   (GIL reacquired)      |                          |
```

This means your FastAPI or aiohttp app can handle other requests while waiting for DynamoDB.

!!! note "Python 3.13+ free-threaded mode"
    Python 3.13 introduced experimental free-threaded mode (no GIL), and 3.14 improves it. Even with free-threading, pydynox benefits from having the heavy work in Rust - serialization runs in parallel without competing for Python's interpreter. When free-threaded Python becomes mainstream, pydynox will work even better.

## Built on AWS SDK for Rust

pydynox uses the official [AWS SDK for Rust](https://aws.amazon.com/sdk-for-rust/) under the hood.

What this means for you:

- **Official support** - The SDK is maintained by AWS, not a third-party library
- **Correct behavior** - Retry logic, error handling, and edge cases follow AWS best practices
- **Future-proof** - As DynamoDB evolves, the SDK evolves with it

You get the ergonomics of a Python ORM with the reliability of an AWS-maintained SDK.

## Key features

pydynox does what you'd expect from a DynamoDB ORM: models, CRUD, queries, batch operations, transactions, and indexes. The interesting parts are:

**Async-first** - Methods are async by default. Use `sync_` prefix for sync code.

**Rust core** - Serialization happens in Rust. This matters for batch operations and queries with thousands of items.

**Auto pagination** - Query and scan iterate through all pages automatically. No more `LastEvaluatedKey` loops.

**Rate limiting** - Built-in RCU/WCU control. No more throttling surprises.

**Pydantic integration** - Use your existing Pydantic models with a decorator. Validation included.

**Memory backend for tests** - Test your code without DynamoDB. Just add a pytest fixture.

**Lifecycle hooks** - Run validation or logging before/after any operation.

**Field encryption** - KMS encryption for sensitive attributes. Transparent to your code.

**S3 attribute** - Store files larger than 400KB. Upload on save, download on demand.

## Get started

Ready to try it? Head to [Getting started](getting-started.md) for installation and your first model.

## Guides

### Core

| Guide | Description |
|-------|-------------|
| [Getting started](getting-started.md) | Installation and first model |
| [Client](guides/client.md) | Configure the DynamoDB client |
| [Models](guides/models.md) | Attributes, keys, defaults, and CRUD |
| [Attributes](guides/attributes.md) | All attribute types |
| [Query](guides/query.md) | Query items with conditions |
| [Scan](guides/scan.md) | Scan and count items |
| [Indexes](guides/indexes.md) | GSI and LSI |
| [Conditions](guides/conditions.md) | Filter and conditional writes |

### Operations

| Guide | Description |
|-------|-------------|
| [Async](guides/async.md) | Async-first API |
| [Batch](guides/batch.md) | Batch get and write |
| [Transactions](guides/transactions.md) | All-or-nothing writes |
| [Tables](guides/tables.md) | Create and manage tables |
| [Atomic updates](guides/atomic-updates.md) | Increment, append, remove |

### Features

| Guide | Description |
|-------|-------------|
| [Hooks](guides/hooks.md) | Before/after operation hooks |
| [Rate limiting](guides/rate-limiting.md) | RCU/WCU control |
| [TTL](guides/ttl.md) | Auto-expire items |
| [Optimistic locking](guides/optimistic-locking.md) | Version-based concurrency |
| [Encryption](guides/encryption.md) | KMS field encryption |
| [S3 attribute](guides/s3-attribute.md) | Large file storage |
| [Projections](guides/projections.md) | Fetch specific fields |
| [Testing](guides/testing.md) | Memory backend for tests |

### Integrations

| Guide | Description |
|-------|-------------|
| [Pydantic](guides/pydantic.md) | Use Pydantic models |
| [Dataclass](guides/dataclass.md) | Use dataclasses |

### Reference

| Guide | Description |
|-------|-------------|
| [Exceptions](guides/exceptions.md) | Error handling |
| [IAM permissions](guides/iam-permissions.md) | Required AWS permissions |
| [Observability](guides/observability.md) | Logging and metrics |
