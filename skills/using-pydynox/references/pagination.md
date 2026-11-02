# Pagination

Use [query_patterns.py](../examples/query_patterns.py). Its `order_page` and
`sync_order_page` functions are reusable examples of returning items plus a
cursor. The `pagination` workflows follow every cursor and assert no missing or
duplicate items, including an empty final result.

## Streaming all matches

Use `async for order in Order.query(partition_key=..., page_size=25)` for a
stream of all matches. Use ordinary `for` with `sync_query`. The iterator
fetches further requests as needed; `page_size` is not an application page limit.

Process each item as it arrives for exports or background jobs. Collecting the
whole iterator in a list also collects the entire result in memory. A sort-key
condition reduces the key range read. A filter discards results after reading.

## Returning a page to an API caller

The example helper takes a customer, an optional full cursor, and a positive
page limit. It returns a list of orders and the next cursor:

1. Construct a fresh `Order.query` with the caller's cursor.
2. Consume the limited iterator completely.
3. Read `result.last_evaluated_key` after iteration.
4. Return items and cursor together.
5. On the next request, reuse the same partition, sort range, filter, and order.

The sync helper uses `sync_query` and `list(result)`. Both are tested against
LocalStack. No count query is needed to implement "load more".

Preserve the whole cursor dictionary. Index cursors can contain both table and
index keys; do not reduce them to one field. An HTTP cursor needs the application's
encoding and scope validation. Keys may contain numbers or bytes, so a generic
JSON encoder is not always sufficient. Do not let a cursor choose another
customer or change the query.

## Request boundaries and returned-item limits

There are three separate boundaries:

| Boundary | What stops |
|----------|------------|
| DynamoDB's response size limit | One service request, possibly before `page_size` items |
| `page_size` | Items evaluated by one request, before filtering |
| pydynox's `limit` | Items yielded to the application across requests |

The current pydynox result stores the cursor at the end of the fetched service
page. It does not move that cursor backward when iteration stops with buffered
items left. For example, `limit=2, page_size=10` can fetch ten items, yield two,
and expose a cursor after the tenth item. Resuming there loses the other eight.
Breaking out of an iterator early has the same problem.

The example uses `page_size=1` so the cursor never points past an unreturned
matching item. It demonstrates correct resumption for arbitrary limits and
filters, at the cost of more requests. Increasing the request size requires
preserving unread items or implementing a cursor tied to the last delivered
item with the complete table/index schema. Test that behavior before changing
the helper. Merely setting `limit=page_size` does not solve every case: filters
and the service response size limit can produce shorter intermediate pages.

For a long-running job that does not need a persisted cursor, keep one iterator
and process all of it with a larger request size.

## Filters and exhaustion

In `filtered_pages`, the first several items do not match. With `page_size=1`,
they produce empty service pages before later matching items. The iterator must
continue while DynamoDB returns a continuation key.

Do not stop a raw pagination loop solely because its `items` list is empty.
Likewise, a nonempty cursor is a continuation opportunity, not proof that another
matching item exists. A final request can return no items and no cursor.

The empty filtered-page iterator fix landed in
[PR #565](https://github.com/ferrumio/pydynox/pull/565) after pydynox 1.8.0.
Check whether the application's installed release includes it. The basic
unfiltered examples run on 1.8.0; `filtered_pages` targets the fixed API.

## Pagination test cases

- Enough items for several application pages and a partial final page.
- Every key appears exactly once after following all cursors.
- A page limit that does not divide the total item count.
- No matching items and several empty filtered service pages.
- Descending order preserved across requests.
- GSI cursors reused without dropping table or index keys.

The memory backend does not produce continuation keys. Use LocalStack for
these cases.

Further reading:

- [pydynox query guide](https://ferrumio.github.io/pydynox/guides/query/)
- [AWS pagination semantics](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Query.Pagination.html)
