# Rate limiting

Control how fast you read and write to DynamoDB. Rate limiting helps you stay within your provisioned capacity and avoid throttling errors.

## Key features

- Fixed rate for known workloads
- Adaptive rate that adjusts based on throttling
- Metrics to track usage

## Getting started

### Why rate limit?

DynamoDB charges for capacity units. When you exceed your provisioned capacity, DynamoDB throttles your requests - they fail with a `ProvisionedThroughputExceededException`.

Rate limiting helps you:

- **Stay within budget** - Don't accidentally burn through capacity
- **Avoid throttling** - Smooth out traffic spikes
- **Share fairly** - Multiple processes can share capacity without fighting

### Fixed rate

Use `FixedRate` when you know exactly how much capacity to use. The rate stays constant unless you change it.

=== "fixed_rate.py"
    ```python
    --8<-- "docs/examples/rate_limit/fixed_rate.py"
    ```

`FixedRate` is good for:

- Batch jobs with predictable throughput
- Background processes that shouldn't use too much capacity
- Sharing capacity between multiple workers

### Adaptive rate

Use `AdaptiveRate` when you don't know the right rate, or when capacity varies. It automatically adjusts based on throttling feedback.

=== "adaptive_rate.py"
    ```python
    --8<-- "docs/examples/rate_limit/adaptive_rate.py"
    ```

How adaptive rate works:

1. Starts at 50% of max rate
2. When throttled, reduces by 20%
3. When no throttle for 10 seconds, increases by 10%
4. Never goes below min or above max

`AdaptiveRate` is good for:

- Variable workloads
- Shared tables where capacity changes
- When you're not sure what rate to use

## Advanced

### Checking metrics

You can see how much capacity you've used and how many times you were throttled:

=== "check_metrics.py"
    ```python
    --8<-- "docs/examples/rate_limit/check_metrics.py"
    ```

This is useful for:

- Monitoring your application
- Tuning your rate limits
- Debugging throttling issues

### FixedRate parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `rcu` | int | None | Read capacity units per second |
| `wcu` | int | None | Write capacity units per second |
| `burst` | int | None | Burst capacity (defaults to rate value) |

**About burst:** DynamoDB allows short bursts above your provisioned rate. If you set `burst=200` with `rcu=50`, you can temporarily read at 200 RCU, but you'll need to slow down afterward to stay within your average.

### AdaptiveRate parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `max_rcu` | int | Required | Maximum RCU per second |
| `max_wcu` | int | None | Maximum WCU per second |
| `min_rcu` | int | 1 | Minimum RCU (won't go below this) |
| `min_wcu` | int | 1 | Minimum WCU (won't go below this) |

### When to use each

| Scenario | Recommendation |
|----------|----------------|
| Known, steady workload | FixedRate |
| Variable workload | AdaptiveRate |
| Batch jobs | FixedRate with high burst |
| Shared capacity | AdaptiveRate |
| Multiple workers | FixedRate, divide capacity by worker count |

### Rate limiting with batch operations

Rate limiting works with batch operations too. The rate limiter tracks capacity used by each batch and waits if needed:

```python
from pydynox import BatchWriter, DynamoDBClient
from pydynox.rate_limit import FixedRate

client = DynamoDBClient(rate_limit=FixedRate(wcu=50))

with BatchWriter(client, "users") as batch:
    for i in range(1000):
        batch.put({"pk": f"USER#{i}", "name": f"User {i}"})
    # Rate limiter ensures we don't exceed 50 WCU
```

!!! tip
    When doing bulk writes, combine rate limiting with batch operations. This gives you both efficiency (fewer API calls) and control (predictable throughput).


## Next steps

- [Encryption](encryption.md) - Field-level encryption with KMS
- [Batch operations](batch.md) - Combine rate limiting with batch writes
- [Observability](observability.md) - Track rate limit metrics
