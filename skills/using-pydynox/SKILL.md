---
name: using-pydynox
description: Build and test Python applications with pydynox for DynamoDB. Use when application code imports pydynox, or the task involves its models, pagination, indexes, writes, or integrations.
license: Apache-2.0
metadata:
  author: ferrumio
  version: "1.1"
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
- Check the installed release, not just the latest documentation. The basic
  examples support 1.8.0. The filtered pagination examples require the fix in
  [PR #565](https://github.com/ferrumio/pydynox/pull/565), which was merged after
  1.8.0. Keep the user's dependency choices and identify missing fixes before
  recommending an upgrade.
- Identify the table, partition key, optional sort key, and access patterns.
  A model declaration does not create a DynamoDB table.
- Use the application's existing client and AWS credential setup. Configure a
  shared client at startup with `set_default_client`, or pass it in
  `ModelConfig(client=...)` when the model needs a specific client.

## Choose the reference for the task

| Task | Read |
|------|------|
| Client setup, models, attributes, reads, writes, conditions, or sync equivalents | [Models and CRUD](references/models-and-crud.md) |
| Automatic pagination, "load more", cursors, limits, or filtered pages | [Pagination](references/pagination.md) |
| Access patterns, sort keys, filters, GSI/LSI, projections, or scans | [Queries and indexes](references/queries-and-indexes.md) |
| Bulk writes, batch reads, conditional writes, or transactions | [Writes and transactions](references/writes-and-transactions.md) |
| Aliases, Decimal, TTL, smart save, hooks, locking, Pydantic, S3, or KMS | [Model features and integrations](references/features-and-integrations.md) |
| Timeouts, throttling, read consistency, metrics, or large workloads | [Operations](references/operations.md) |
| Application tests, memory fixtures, or LocalStack | [Testing](references/testing.md) |

Read the relevant reference and its linked example before implementing the task.
The [application example](examples/application.py) covers CRUD, batches, write
conditions, atomic updates, and transactions. The
[query examples](examples/query_patterns.py) cover streaming, cursor pagination,
filters, sort order, projections, GSI queries, and scans. Both include async and
sync workflows with assertions.

## Choose the read operation

| Application needs | Use |
|-------------------|-----|
| One item with its complete primary key | `await Order.get(pk=..., sk=...)`; handle `None` |
| Items in one partition | `Order.query(partition_key=...)` |
| A prefix or range within that partition | Add `sort_key_condition=Order.sk.begins_with(...)` or `.between(...)` |
| Another partition key, such as customer plus status | Declare and query a `GlobalSecondaryIndex` |
| Several known, unrelated full keys | `await Order.batch_get(keys)`; match results by key |
| A table-wide export or maintenance job | Stream `Order.scan()`; consider a parallel scan for large jobs |

`query` and `scan` are lazy iterators, not awaitable lists. Use `async for`, or
`for` with `sync_query` / `sync_scan`. For one result, use
`await Order.query(...).first()` or `Order.sync_query(...).first()`.
Choose the key condition or index before adding a filter.

## Pagination is part of the application API

Decide whether the caller needs a stream of all matches or a bounded page plus
a continuation cursor. These are different return contracts.

| Parameter | Meaning |
|-----------|---------|
| `limit` | Maximum items yielded by this iterator |
| `page_size` | Maximum items evaluated per DynamoDB request, before filtering |
| `last_evaluated_key` | Full key dictionary used to resume the same query |
| `scan_index_forward=False` | Descending sort-key order; keep it unchanged when resuming |

For an export, iterate the result and let it fetch pages. Setting `page_size=25`
does not limit the total output to 25 items. Avoid collecting an unbounded query
into a list.

For "load more", keep the result object, consume the bounded iterator, then
return its `last_evaluated_key` with the items. Resume using the same partition,
sort condition, filter, index, and ordering. Do not translate a page number into
an offset: DynamoDB uses continuation keys.

The current iterator exposes the fetched page's cursor. Stopping partway through
that page can skip buffered items when resuming, including when `limit` is smaller
than `page_size`. The bundled `order_page` and `sync_order_page` helpers use
`page_size=1` to keep every returned item on a request boundary. This costs more
requests; read [Pagination](references/pagination.md) before changing that
tradeoff or designing a larger-page cursor.

Filters run after reads. An empty service page can still have a continuation
key; a nonempty cursor does not promise another matching item. Cover empty
filtered pages, resumption, and exhaustion in LocalStack tests.

## Choose the write operation

| Application needs | Use and check |
|-------------------|---------------|
| Create only if absent | `save(condition=Order.pk.not_exists())` |
| Change a few fields | `update(status=...)`; add a condition for state transitions |
| Increment a counter | `update(atomic=[Order.total_cents.add(100)])` |
| Save edits to a loaded model | `save()` uses smart save; inspect `changed_fields` |
| Detect a stale edit | Add `VersionAttribute`; reload before a bounded retry |
| Write independent items in bulk | `BatchWriter` / `SyncBatchWriter` |
| Commit related changes together | `Transaction` / `SyncTransaction` |

Await async operations in this table. Batch and transaction queue methods such
as `batch.put` and `tx.save_model` are synchronous; their context managers flush
or commit on successful exit. A batch writer does not provide transaction
atomicity. See [Writes and transactions](references/writes-and-transactions.md)
for rejection and rollback examples.

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

## Use library features when the task calls for them

- Use aliases for stored field names and `DecimalAttribute` for exact scalar
  decimals. Raw client data and model values have different conversion rules.
- Use `TTLAttribute` and `ExpiresIn` for expiry, and check expiry in application
  reads that must reject expired records before DynamoDB removes them.
- Use `VersionAttribute`, lifecycle hooks, and smart save with their documented
  semantics; raw batch writes do not provide the model save lifecycle.
- Use `dynamodb_model` for an existing Pydantic model or dataclass rather than
  maintaining a second schema.
- Read the S3, KMS, compression, and size guides before storing large or encrypted
  payloads. Check the limits of the operation being used, including transactions.
- For key templates, inheritance, distributed locks, PartiQL, vector search,
  and observability, follow the task-specific links in
  [Model features and integrations](references/features-and-integrations.md).

Use [Operations](references/operations.md) for runtime configuration and
[Testing](references/testing.md) to choose the backend. Memory tests cannot
verify continuation cursors, transactions, indexes, or AWS behavior.
