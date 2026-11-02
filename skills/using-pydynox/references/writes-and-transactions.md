# Writes, batches, and transactions

Read [application.py](../examples/application.py) for async and sync workflows.

## Conditions and atomic updates

`save(condition=Order.pk.not_exists())` provides create-only behavior for the
item's complete key. A get-then-save check can race with another writer.

Use a condition on the stored state for a transition:
`await order.update(status="paid", condition=(Order.status == "pending"))`.
Catch `ConditionalCheckFailedException` when rejection is an expected conflict.
The `crud` examples test both successful writes and rejected duplicates or
stale state transitions.

For counters, use `atomic=[Order.total_cents.add(100)]`. A Python read,
increment, and save can lose another writer's update. Conditions can be
combined with atomic actions, for example a stock decrement that must not
make inventory negative.

The atomic update guide also covers setting, removing, appending, set
operations, and `if_not_exists`. Use `ListAttribute`, `MapAttribute`, and set
attributes with the appropriate operation; verify memory backend support
before choosing the test fixture.

## Batch reads

`await Order.batch_get(keys)` takes full key dictionaries and returns model
instances. `Order.sync_batch_get(keys)` is synchronous. Missing items are
omitted and results need not preserve input order.

Match by complete key to rebuild application order. With a composite key,
matching only `pk` would collapse distinct items in the same partition.
Deduplicate input keys and choose consistent reads when needed.

Use model field names for `Model.batch_get` keys and stored attribute names
for raw client operations when the schema has aliases.

## Batch writes

Queue raw item dictionaries with `batch.put(item)` and keys with
`batch.delete(key)`. These calls are synchronous for both `BatchWriter` and
`SyncBatchWriter`. The successful context exit flushes writes; the client
handles request splitting and unprocessed-item retries.

Use batches for independent writes. They do not support per-item conditions
or all-or-nothing commits. If a later request fails, earlier requests may have
succeeded. Plan application retries with that partial progress in mind.

Raw batch dictionaries do not run model `save` hooks or optimistic version
checks. Serialize model values deliberately with `to_dict()` and check any
attribute-specific requirements, such as S3 or encrypted values.

## Transactions

Use `async with Transaction(client) as tx` or
`with SyncTransaction(client) as tx`. Queue with `tx.put`, `tx.update`,
`tx.delete`, `tx.condition_check`, or `tx.save_model`. Queuing is synchronous;
the context commits on successful exit.

Conditions on writes and condition checks use DynamoDB expressions for raw
operations. Use expression name/value placeholders. Do not concatenate user
input into an expression.

Do not queue two actions targeting the same item in one transaction.
Put the condition on its write rather than combining a separate condition
check and update for that same item.

The `transaction` examples first commit a group of writes, then deliberately
fail a condition in another transaction and assert that its new item was not
written. A failed service condition raises `TransactionCanceledException`.
Inspect the failure before retrying: a business rule rejection will not be
fixed by repeating the request.

For an ambiguous transport failure, `client_request_token` can make retries of
the same transaction idempotent within the service's documented window. Reuse
the token and identical parameters for the same logical attempt. Use a new token
for a different operation. Consult the transaction guide for limits and
supported model features before using transaction model helpers.

Further reading:

- [Conditions](https://ferrumio.github.io/pydynox/guides/conditions/)
- [Atomic updates](https://ferrumio.github.io/pydynox/guides/atomic-updates/)
- [Batch operations](https://ferrumio.github.io/pydynox/guides/batch/)
- [Transactions](https://ferrumio.github.io/pydynox/guides/transactions/)
