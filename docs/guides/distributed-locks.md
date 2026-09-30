# Distributed locks

Coordinate work on the same resource across services, scripts, queue workers,
Lambda, and ECS. Callers using the same table, Region, and resolved key compete
for one lock.

## Lock a function

```python
from pydynox import DynamoDBClient
from pydynox.lock import distributed_lock

client = DynamoDBClient()


@distributed_lock(
    client,
    table="locks",
    key="customer-sync:{customer_id}",
)
async def synchronize_customer(customer_id: str):
    await import_orders(customer_id)
    await update_summary(customer_id)
```

The same decorator works with `def`. Each call acquires before entering the
function, renews during execution, and attempts release on return, exception,
or cancellation. Decorating or creating an unawaited coroutine makes no requests.
Return values, function signatures, and application exceptions are preserved.

Create the table once during deployment:

```python
client.sync_create_table("locks", partition_key=("key", "S"), wait=True)
```

Use a dedicated table with a string partition key named `key`, no sort key, and
TTL disabled. Runtime lock operations do not create or configure tables.

## Timing and errors

| Option | Default | Meaning |
|--------|---------|---------|
| `lease_duration` | 30 seconds | Renewal window; attempts run every third of this duration |
| `wait_timeout` | 35 seconds | How long acquisition may wait; excludes function execution |

A function can run for ten minutes with a 30-second lease as long as renewal
keeps succeeding. A contender with a five-second wait stops after its own budget.
The library never retries the function body.

`wait_timeout=0` makes an immediate attempt without sleeping for contention.
Network requests still take time. Both durations must be finite and at most
86,400 seconds; the minimum lease is 0.1 seconds. Use realistic network margins
in production.

| Result | Behavior |
|--------|----------|
| Another worker keeps the lock | Raise `LockNotAcquired`; do not enter the body |
| Ownership expires or changes | Raise `LockLost` on a local check or successful-body exit |
| Release cannot be confirmed | Raise `LockReleaseError` after a successful body |
| Body and cleanup both fail | Preserve the body exception and attach a cleanup note |
| Missing table, denied access, connection failure | Preserve the relevant pydynox error during acquisition |

Import these exceptions from `pydynox.exceptions`. Decide how your application
retries contention; queue workers should not acknowledge unfinished work as
successful.

## Lock a block and protect database writes

Use `DistributedLock` for async code or `SyncDistributedLock` for sync code:

```python
from pydynox.lock import DistributedLock
from pydynox.transaction import Transaction

async with DistributedLock(client, table="locks", key="customer-sync:123") as lease:
    result = await prepare_summary()
    lease.raise_if_lost()
    async with Transaction(client) as transaction:
        lease.check_in(transaction)
        transaction.put("summaries", {"customer_id": "123", "summary": result})
```

`raise_if_lost()` checks local validity. It cannot make a later side effect atomic
with ownership. `check_in()` adds an ownership condition to the **same transaction**
as your writes, so DynamoDB rejects the transaction after release or takeover.
Commit inside the lock block using the same client. The check uses one transaction
item; do not include another operation on that lock item.

A process can pause, lose its lease, and resume its code. Neither the decorator
nor a local check forcibly stops arbitrary Python code. For external side effects,
the destination needs its own stale-write protection. Owner UUIDs are identities,
not ordered fencing tokens.

## Recovery and lifecycle

After a crash, renewal stops. A contender first reads the current version, waits
the **stored owner's lease**, and can take over only if that version stays unchanged.
This avoids comparing timestamps from different machines.

For example, observing an abandoned 30-second lease at 15s allows a takeover
attempt around 45s. An old row does not let a fresh client skip observation.
Repeated short or zero-wait calls on the same client retain observations. New
clients lose that history; repeated five-second waits with fresh clients cannot
recover a 30-second lease. The cache holds up to 4,096 resource observations;
eviction can delay recovery.

Guards are single-use and locks are not reentrant. Nested acquisition of the same
key competes like any other caller. Acquire multiple resources in a consistent
order. There is no FIFO or starvation guarantee.

Use a client per process and create it inside the worker. Start worker processes
before creating clients, or use the multiprocessing `spawn` method. Inherited
clients and guards are rejected after `fork`. A client supports multiple threads
and successive async event loops. Keep the context inside the invocation; do not
leave an active guard behind when closing an event loop.

Renewal runs on the shared Rust runtime. It can continue while Python code or its
event loop is stuck. Set an application execution deadline and arrange shutdown
of stalled workers. SIGKILL, container termination, or a Lambda hard timeout
requires abandoned-lock recovery. For graceful shutdown, let active contexts exit.

## Keys

Templates accept direct argument names, including defaults, positional arguments,
and keyword arguments. Referenced values must be strings; convert numeric IDs
explicitly before calling. Bound methods work. Other decorators must preserve the
function's sync/async interface. Generators and async generators are rejected.

`"customer:{customer_id}"` with `"123"` resolves to `"customer:123"`. Multiple
placeholders use UTF-8 byte lengths to avoid delimiter collisions:
`"{tenant}:{id}"` with `"acme"` and `"123"` resolves to `"4:acme:3:123"`.
Use `{{` and `}}` for literal braces. Resolved keys must contain 1–2,048 UTF-8 bytes.
Share the same template across services that should coordinate.

## Requests and metrics

An uncontended call that finishes before renewal uses **two writes**: acquisition
and release. Each confirmed renewal adds one write. A ten-minute hold with the
default interval is roughly 61–62 writes, depending on timing.

```python
print(lease.metrics.write_requests)
print(lease.metrics.read_requests)
print(lease.metrics.renewals)
print(lease.metrics.wait_ms)
```

Snapshots also expose `conditional_failures`, `request_failures`, `wait_timeouts`,
`cleanup_failures`, `lost`,
`consumed_rcu`, and `consumed_wcu`. Reads include contention polling and ambiguous
write reconciliation. Capacity totals include only successful responses that
report capacity. Failed conditions and lost responses can still consume capacity;
these totals are not the bill. MemoryBackend reports zero real capacity.

Lock metrics are separate from the client's operation totals. Lock requests use
the client's AWS configuration with SDK retries disabled for the lock protocol.
Rust bounds each request and handles renewal retries. Client rate limiting does
not delay heartbeats. Unrelated client calls keep their configuration.

## Storage and timing contract

Protocol version 1 stores `key`, `owner`, `version`, `lease_ms`, and `protocol`.
Acquisition uses a conditional put; takeover and renewal match owner and version.
Release matches the unique acquisition owner. Unknown protocols and malformed
rows fail without takeover. Do not edit these rows or add TTL cleanup.

Owner validity starts **before** the write and ends at 90% of the lease unless
renewal is confirmed. It checks both monotonic elapsed time and local wall time.
Clock jumps can cause early loss. Safety assumes elapsed clocks have bounded rate
differences within that margin; arbitrary clock faults are unsupported. Contender
observation uses monotonic time. Request timeouts are at most one-third of the
lease and five seconds. Cleanup has a total budget of 60% of the lease, capped at
ten seconds, including any in-flight request and reconciliation.

A timed-out write may have committed. Acquisition and renewal reconcile the
exact attempted owner/version within their deadline. Late success never revives
a lost or cancelled guard. A put that reaches DynamoDB after cancellation and
cleanup can leave an abandoned row; normal observation recovers it.

Use one Region and one table with strongly consistent reads. Cross-Region
coordination, including Global Tables, is outside the supported scope. Table deletion, restore,
or external row deletion breaks the protocol's storage assumptions. Stop all
workers before replacing storage, then restart them with fresh clients and guards.

## Examples and testing

=== "Async worker"
    ```python
    --8<-- "docs/examples/distributed_locks/worker.py"
    ```

=== "Sync script"
    ```python
    --8<-- "docs/examples/distributed_locks/sync_script.py"
    ```

A Lambda handler can call the same decorated sync function as an ECS worker:

```python
def handler(event, context):
    synchronize_customer(event["customer_id"])
```

Here `synchronize_customer` must be the `def` version. Set its acquisition budget
below the invocation's remaining execution time and leave room for work and cleanup.

MemoryBackend runs the native protocol against its testing store. It supports
decorators, contexts, contention, and renewal, but does not simulate process
failure, network timing, or transactions. Integration tests use the AWS SDK against
LocalStack and separate processes; run AWS environment validation before relying
on production timing estimates.
