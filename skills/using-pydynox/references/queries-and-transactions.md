# Queries and transactions

Read [application.py](../examples/application.py) for `query_and_batch`,
`pagination`, and `transaction`, plus their `sync_` equivalents.

## Query and pagination

Use `Order.query(partition_key=...)` when the partition key is known. Add
`sort_key_condition=Order.sk.begins_with("ORDER#")` for a sort-key prefix.
Use an appropriate index for another access pattern; a scan reads across the
table.

Iterate a query with `async for order in Order.query(...)`. The query itself is
not awaited. In sync code, use `for order in Order.sync_query(...)`.

The iterator fetches additional pages. `limit` caps the number of returned
items; `page_size` controls the requested page size. For a continuation cursor,
consume the limited result and pass its `last_evaluated_key` to the next query.
Use that cursor with the same query parameters.

`filter_condition` filters items after DynamoDB reads them. It does not replace
a key condition or reduce read capacity for the items examined. A filtered page
can be empty and still have a continuation key. Let the iterator handle
pagination.

See the [query guide](https://ferrumio.github.io/pydynox/guides/query/) for
projection, ordering, and pagination examples.

## Batch operations

`await Order.batch_get(keys)` accepts a list of complete key dictionaries.
Results can be unordered and missing items are omitted. Match results by key
when the application needs to preserve input order.

Use `async with BatchWriter(client, table) as batch` for bulk puts and deletes.
`batch.put(item)` and `batch.delete(key)` queue operations without `await`; the
context flushes pending writes on exit. In sync code, use `SyncBatchWriter`
with an ordinary `with` block.

Batch writes are useful for independent operations. For all-or-nothing writes,
use a transaction.

See [batch operations](https://ferrumio.github.io/pydynox/guides/batch/) for
request splitting, retries, and projections.

## Transactions

Use `async with Transaction(client) as tx`, or `with SyncTransaction(client) as tx`.
Queue raw items with `tx.put(table, item)` or models with `tx.save_model(model)`.
These queueing methods are synchronous in both classes. The context commits on
successful exit.

Transactions can contain writes and condition checks. A failed condition aborts
the transaction and raises `TransactionCanceledException`. Do not queue two
actions for the same item in one transaction.

When an application retries the same transaction after an ambiguous failure,
consider `client_request_token` and keep the request parameters identical.
Read the [transaction guide](https://ferrumio.github.io/pydynox/guides/transactions/)
for token lifetime, limits, and retry behavior.

Use LocalStack for pagination, transaction, and GSI tests. The memory backend
does not provide continuation keys or implement transactions and GSI.
