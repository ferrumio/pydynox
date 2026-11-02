# Queries, indexes, and scans

Read [query_patterns.py](../examples/query_patterns.py) for model declarations
and executable workflows. It uses a customer partition and an order sort key,
plus a GSI for customer and status.

## Start from the access pattern

| Question | Shape |
|----------|-------|
| Fetch one order | `Order.get` with both key fields |
| All orders for a customer | `Order.query(partition_key=customer_pk)` |
| Orders in a key prefix | Add `Order.sk.begins_with("ORDER#")` |
| Orders in an inclusive key range | Add `Order.sk.between(start, end)` |
| Newest orders first | `scan_index_forward=False` with a sortable key |
| Customer orders in one status | Query the example's `customer_status_index` |
| Export every order | Stream a scan; account for table-wide read cost |

String sort keys sort lexicographically. Use a consistent timestamp format or
zero-padded sequence if that order must match application order.

Use key attributes in the key condition. Use `filter_condition` for non-key
attributes. Combine conditions with `&` / `|`, and parenthesize comparisons;
Python `and` / `or` do not build DynamoDB expressions.

The `query_options` workflows combine a sort-key range, a status filter,
descending order, and a projection. They assert exactly which items and fields
are returned.

## Secondary indexes

Declare a `GlobalSecondaryIndex` as a model class attribute, with the deployed
index name, partition-key field, and optional sort-key field. The example uses
a derived `customer_status` field so a status lookup is still scoped to a
customer. Maintain that field when the status changes.

Call `Order.customer_status_index.query(partition_key=...)`, or its
`sync_query` equivalent. Index queries use the index partition key, not the
base table's partition key. They support sort conditions, filters, ordering,
limits, page sizes, and continuation keys.

The declaration alone does not add an index to an existing table. Provision
the matching schema through the application's infrastructure. The example
creates a separate LocalStack table with its declared index.

GSI reads are eventually consistent. Do not request strong consistency or
promise immediate index visibility after a write. The example waits with a
deadline for its seeded index data before checking pagination.

Check the deployed index projection: `ALL`, `KEYS_ONLY`, or selected attributes.
A GSI cannot return arbitrary fields that were not projected. Fetch the complete
base-table items by their keys if the application needs them.

A `LocalSecondaryIndex` shares the table's partition key and provides a
different sort key. It must be created with the table. Read the index guide
before choosing an LSI or multi-attribute index schema.

## Projections and result shape

Model queries and scans accept `fields=["pk", "sk", "status"]`. Use model field
names; pydynox handles expression names. Keep the keys if the result will be
identified or used for a later read.

`as_dict=True` returns dictionaries rather than model instances. It still uses
the model's conversion rules; a `DecimalAttribute` can remain a `Decimal`.
This is not a promise of JSON-safe values or the same types as raw client reads.

A projected object is partial data. Do not save it as a complete replacement
or treat missing projected fields as authoritative defaults. Projections
reduce returned data and decoding work, not the capacity charged for the
underlying table read.

## Scans and counts

`Model.scan()` is an async iterator; `sync_scan()` is a sync iterator. The
`scan_items` workflows stream projected dictionaries and check all seeded keys.
Filtering a scan does not turn it into a key lookup.

For parallel scans, use the documented `parallel_scan(total_segments=...)` API
and plan read capacity. A resumable segmented scan needs a cursor for each
segment, with the same segment count on resumption.

`await Model.count()` and `Model.sync_count()` return `(count, metrics)`.
They perform read work; do not add an exact total to every paginated endpoint
without considering its cost. Reads across several requests are not a stable
snapshot while other clients modify the table.

Further reading:

- [Indexes](https://ferrumio.github.io/pydynox/guides/indexes/)
- [Projections](https://ferrumio.github.io/pydynox/guides/projections/)
- [Scan](https://ferrumio.github.io/pydynox/guides/scan/)
- [Single-table design](https://ferrumio.github.io/pydynox/guides/single-table/)
- [AWS GSI behavior](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/GSI.html)
