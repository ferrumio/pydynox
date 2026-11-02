# Running an application

## Clients, credentials, and timeouts

Create and reuse `DynamoDBClient` instances at application startup. Register the
shared client with `set_default_client` or select one through `ModelConfig`.
Use the application's AWS SDK credential source: environment, profile, role,
or workload credentials. Keep dummy static credentials in local tests.

For LocalStack, supply its endpoint, region, and dummy credentials together.
For remote AWS, confirm the application's region and table/index names.
A model class does not create infrastructure.

Check the installed constructor before adding options such as `connect_timeout`,
`read_timeout`, profile/role settings, or a proxy. Their interactions have had
fixes after 1.8.0. Use the relevant release's client guide and avoid changing
process-wide environment settings to configure one application client.

## Consistency and read cost

Use `consistent_read=True` for table reads that need to observe an acknowledged
write. It can be passed on a read or configured in `ModelConfig`. GSI queries
are eventually consistent; a successful base-table write does not guarantee
that the updated index entry is immediately visible.

Filters and projections do not reduce the number of table bytes evaluated for
capacity. Prefer a suitable key/index for a frequent access pattern. Repeatedly
scanning a table to answer a customer lookup is usually a schema problem.

Strong reads do not create a snapshot across all pages or make a
read-modify-write sequence atomic. Use write conditions, atomic actions,
optimistic locking, or a transaction for those requirements.

## Throttling, retries, and concurrency

Use the documented `FixedRate` or `AdaptiveRate` configuration for a workload
that needs read/write pacing. Check the version's SDK and rate-limiter retry
behavior before adding another application retry loop.

Classify errors: a failed condition, access denial, invalid expression, and
throttling require different responses. Catch the documented exceptions from
`pydynox.exceptions`. Retry bounded transient work with appropriate backoff;
repeating a non-idempotent write after an ambiguous timeout can apply it twice.

Bound concurrent requests in a worker or API. An unbounded `asyncio.gather`
over an entire scan can turn a streaming read into a memory and throughput
spike. For independent bulk writes use a batch writer; for a large export
stream the iterator.

## Metrics and diagnosis

Use the documented `get_last_metrics()` / `get_total_metrics()` model methods
to inspect request duration and consumed capacity. The observability guide
also covers OpenTelemetry integration and optional dependencies.

When a request behaves unexpectedly, inspect its region, table/index, key
shape, expression, and exception before changing retries. For pagination,
inspect the cursor and distinguish the evaluated-item page size from the
number of returned matches.

Further reading:

- [Client](https://ferrumio.github.io/pydynox/guides/client/)
- [Rate limiting](https://ferrumio.github.io/pydynox/guides/rate-limiting/)
- [Observability](https://ferrumio.github.io/pydynox/guides/observability/)
- [Exceptions](https://ferrumio.github.io/pydynox/guides/exceptions/)
- [IAM permissions](https://ferrumio.github.io/pydynox/guides/iam-permissions/)
- [Hot partitions](https://ferrumio.github.io/pydynox/guides/diagnostics/hot-partition/)
