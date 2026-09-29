# ADR 021: Distributed locks

## Status

Proposed — RFC. The API below does not exist yet.

## Context

Several workers may try to import data for the same customer, process the same
resource, or run a scheduled job. They need a shared way to coordinate access
across processes and machines.

Add a lock helper backed by DynamoDB, usable with the existing client and
independent of models or agent frameworks. The AWS DynamoDB Lock Client is a
reference for the lease protocol.[1][2]

This is a cooperative lock. It does not make external side effects atomic or
guarantee that a job runs exactly once.

## Decision

### Proposed API

Expose `DistributedLock` and `SyncDistributedLock` from `pydynox.lock`.
Both use the same protocol, options, and errors.

```python
from pydynox.lock import DistributedLock

async with DistributedLock(
    client,
    table="locks",
    key=f"import:customer:{customer_id}",
) as lock:
    await prepare_import(customer_id)
    lock.raise_if_lost()
    await finish_import(customer_id)
```

The sync equivalent uses `with SyncDistributedLock(...)`.
`raise_if_lost()` only checks the local lease state. It cannot make the next
operation atomic with ownership of the lock.

| Argument | Proposed default | Meaning |
|----------|------------------|---------|
| `client` | Required | Existing `DynamoDBClient` |
| `table` | Required | Lock table name |
| `key` | Required | Non-empty string identifying the resource |
| `lease_duration` | `30.0` | Seconds without a confirmed renewal before ownership is lost |
| `wait_timeout` | `35.0` | Acquisition budget in seconds; `0` disables waiting |

Renew automatically every `lease_duration / 3`. Keep this interval internal.
Validate finite durations, a positive lease, and a nonnegative wait.
A guard is single-use and cannot be entered recursively or shared by concurrent
tasks. Callers create a new guard for every acquisition.

### Lambda experience

For an HTTP Lambda, a caller may prefer an immediate conflict response:

```python
from pydynox import DynamoDBClient
from pydynox.exceptions import LockNotAcquired
from pydynox.lock import SyncDistributedLock

client = DynamoDBClient()


def handler(event, context):
    customer_id = event["pathParameters"]["customer_id"]
    try:
        with SyncDistributedLock(
            client,
            table="locks",
            key=f"import:customer:{customer_id}",
            wait_timeout=0,
        ):
            import_customer_data(customer_id)
        return {"statusCode": 200, "body": "Import complete"}
    except LockNotAcquired:
        return {"statusCode": 409, "body": "Import already in progress"}
```

Keep the client outside the handler and the guard inside it. Stop renewal and
finish bounded cleanup before returning. Lambda can freeze an execution
environment between invocations; a hard timeout may skip cleanup entirely.[3]

`wait_timeout=0` has an important limit: a fresh invocation cannot establish that
an existing row is abandoned from one read. With the protocol below, recovery
requires a contender willing to observe a full lease. If every caller always
uses zero wait, a crashed owner's row will remain unavailable. An application
using the HTTP pattern above must also have a recovery path that waits.

For background Lambdas, use a wait budget that allows this observation, and leave
time for the work and cleanup within the invocation timeout. A failed acquisition
from SQS should be retried through the configured batch failure handling when the
message still needs processing. Returning success can acknowledge the message.[4]

### Table and ownership protocol

Use a dedicated table with a string partition key named `key`, no sort key, and
no secondary indexes. Provision it before use. Runtime permissions are
`GetItem`, `PutItem`, `UpdateItem`, and `DeleteItem`.

Each row contains `key`, a random `owner_id` for this acquisition, a random
`record_version`, and `lease_duration`. Every acquisition and renewal changes
the version. These UUIDs identify ownership; they are not ordered fencing tokens.

Use strongly consistent reads and conditional writes:

1. Create a missing row with `attribute_not_exists(key)`.
2. For an existing row, remember its version and lease duration. Observe elapsed
   time with a local monotonic clock. A changed version restarts observation.
3. After a full observed lease without a version change, attempt takeover with a
   condition on the observed owner and version. Competing contenders cannot both
   satisfy that condition.
4. Renew only when owner and version still match. Release with the same checks,
   after stopping and joining the renewal task.

This follows the version observation approach described by AWS.[1][2] Waiting
uses bounded polling with jitter. The acquisition budget includes observation
and request retries. Zero wait still requires network requests.

Do not use wall-clock expiry comparisons or DynamoDB TTL to decide ownership.
TTL deletion is asynchronous and can happen days after expiry.[5] Version 1
should leave TTL disabled on the lock table. A clean exit deletes the row;
an abandoned row is reused by a waiting contender.

### Failures and loss of ownership

Use a conservative local deadline measured from the start of the last confirmed
acquisition or renewal request. Never extend it merely because a request was sent.
Only expose an acquired guard if a useful lease remains when the response arrives.

| Event | Required behavior |
|-------|-------------------|
| Lock remains unavailable within the wait budget | Raise `LockNotAcquired`; do not enter the block |
| Renewal condition fails or local deadline passes | Mark the guard permanently lost and stop renewing |
| Write response times out | Reconcile using a strong read and the attempted owner/version, within the original deadline |
| Ownership cannot be confirmed in time | Do not start or continue claiming ownership |
| Late response arrives after loss or cancellation | Never revive the guard or extend its lease |
| Process dies | A waiting contender can recover after observing an unchanged lease |
| Old owner releases after takeover | Its conditional delete must not remove the new owner's row |

At most one renewal request may be in flight for a guard. SDK retries must reuse
the attempted version and fit inside the remaining lease budget. A late response
may leave a row to be recovered, but must never start background renewal after
the guard has exited.

`LockNotAcquired` and `LockLost` inherit from `PydynoxException` and are exported
from `pydynox.exceptions`. Preserve existing AWS exceptions for failures such as
missing tables, invalid credentials, and denied access.

After ownership is lost, `raise_if_lost()` raises `LockLost`. Exiting an otherwise
successful block also raises it. Neither interface can forcibly interrupt
arbitrary application code. If the block is already raising an exception or
being cancelled, preserve that exception and report cleanup failures separately.
On a successful body, an unresolved release error must be reported to the caller.

A paused worker can resume after another worker has acquired the lock. Operations
that must reject stale workers need ownership checks enforced by the destination,
such as fencing or a condition in the same DynamoDB transaction as the write.[6]
Automatic fencing of external systems and automatic retries of user code are
outside this proposal.

### Implementation boundary

Put the protocol, conditional requests, deadlines, and renewal task in Rust using
the existing AWS SDK and Tokio runtime. Python provides the two context managers
and errors. Sync waiting must release the GIL, and blocking Python work must not
prevent the native renewal task from running.

Bound request and cleanup time, propagate async cancellation, and stop renewal
without leaving tasks alive across Lambda invocations. Do not mutate the shared
client's retry or timeout configuration. Add no Python runtime dependency.

Version 1 supports one Region and one lock per guard. Global Tables, fair queues,
reentrant locks, acquiring several locks together, and leader election helpers
are outside the initial scope.

## Reasons

- Works with the client directly, across application frameworks.
- Fits the project's async and sync API convention.
- Gives acquisition, renewal, and cleanup one shared contract.
- Uses elapsed time and version checks instead of assuming synchronized clocks.
- Leaves existing client and model behavior unchanged.

## Alternatives considered

| Alternative | Tradeoff |
|-------------|----------|
| Conditional writes or optimistic versions alone | Prefer them when coordination only protects one atomic database change |
| Idempotency records | Track repeated operations and results; a lock only coordinates concurrent access |
| An existing DynamoDB lock library | Avoids maintaining a protocol; evaluate its Python, async, and lifecycle support before building |
| Absolute expiry timestamps | Easier recovery from a single read, but requires explicit clock-skew assumptions |
| DynamoDB TTL as the lease | Cleanup timing cannot provide lease timing[5] |
| Redis, a queue, or a workflow service | May fit applications that already use those services |

## Consequences

Holding a lock adds a write for each renewal, plus acquisition and release work.
Contention adds reads, conditional write attempts, and waiting time. Measure
consumed capacity instead of promising a fixed cost or throughput.

Expired or lost ownership does not roll back completed work. Applications still
need their own retry and idempotency policy, especially after an ambiguous result.

### Validation before implementation is considered complete

- Deterministic clock tests for renewals, takeover, deadlines, and wall-clock jumps.
- Async and sync tests for simultaneous contenders, independent keys, cancellation,
  stale release, throttling, ambiguous responses, and late request completion.
- Multi-process tests that kill or pause an owner and observe a successor.
  Verify that a resumed owner reports loss without claiming its user code stopped.
- MemoryBackend parity for conditions and the guard lifecycle.
- Lambda tests for warm reuse, hard timeout, and bounded cleanup; SQS batch examples.
- Benchmarks for acquire/release latency, contention, heartbeat capacity, and
  recovery time. Record Region, item size, lease settings, and concurrency.

### Questions for RFC review

1. Are the proposed 30-second lease and 35-second wait useful defaults?
2. Is full-lease observation acceptable for Lambda recovery, given the zero-wait
   limitation, or should we evaluate a different expiry protocol first?
3. Should an atomic ownership check for protected DynamoDB transactions be part
   of version 1, so users can reject stale writes?

## References

1. [Amazon DynamoDB Lock Client](https://github.com/awslabs/amazon-dynamodb-lock-client)
2. [Building distributed locks with the DynamoDB Lock Client](https://aws.amazon.com/blogs/database/building-distributed-locks-with-the-dynamodb-lock-client/)
3. [Lambda execution environment lifecycle](https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtime-environment.html)
4. [Using Lambda with Amazon SQS](https://docs.aws.amazon.com/lambda/latest/dg/with-sqs.html)
5. [DynamoDB time to live](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/TTL.html)
6. [Leader election in distributed systems](https://aws.amazon.com/builders-library/leader-election-in-distributed-systems/)
