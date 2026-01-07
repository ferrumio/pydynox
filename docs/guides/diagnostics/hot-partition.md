# Hot partition detection

Detect when a single partition key gets too much traffic.

DynamoDB partitions have limits: [~1000 WCU/s for writes and ~3000 RCU/s for reads](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/bp-partition-key-design.html#bp-partition-key-throughput-bursting). When you hit these limits, DynamoDB throttles your requests. The hot partition detector warns you before that happens.

## Key features

- Track writes and reads per partition key
- Sliding window counter (configurable duration)
- Per-table threshold overrides
- Per-model threshold overrides via `ModelConfig`
- Logs warnings when thresholds are exceeded

## Getting started

Create a `HotPartitionDetector` and pass it to your client:

=== "hot_partition_basic.py"
    ```python
    --8<-- "docs/examples/diagnostics/hot_partition_basic.py"
    ```

When a partition exceeds the threshold, you'll see a warning in your logs:

```
WARNING:pydynox.diagnostics:Hot partition detected - table="events" pk="EVENTS" had 500 writes in 60s
```

## Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `writes_threshold` | int | Max writes per window before warning |
| `reads_threshold` | int | Max reads per window before warning |
| `window_seconds` | int | Sliding window duration in seconds |

All parameters are required. There are no defaults.

## Per-table overrides

Some tables handle more traffic than others. Use `set_table_thresholds()` to set different limits:

=== "hot_partition_table_override.py"
    ```python
    --8<-- "docs/examples/diagnostics/hot_partition_table_override.py"
    ```

## Per-model overrides

You can also set thresholds in `ModelConfig`. This is useful when different models share the same client:

=== "hot_partition_model_override.py"
    ```python
    --8<-- "docs/examples/diagnostics/hot_partition_model_override.py"
    ```

Model thresholds take precedence over client thresholds.

## How it works

The detector uses a sliding window counter:

1. Each write/read operation is recorded with a timestamp
2. Old entries (outside the window) are cleaned up
3. When the count exceeds the threshold, a warning is logged

The tracking happens in Rust for speed. The Python wrapper adds logging and threshold overrides.

## Choosing thresholds

DynamoDB partition limits are:

- ~1000 WCU/s per partition (writes)
- ~3000 RCU/s per partition (reads)

But these are theoretical maximums. In practice, set thresholds lower to catch problems early:

| Use case | Writes | Reads | Window |
|----------|--------|-------|--------|
| Conservative | 500 | 1500 | 60s |
| Moderate | 800 | 2500 | 60s |
| High traffic | 2000 | 5000 | 60s |

!!! tip
    Start with conservative thresholds. If you get too many false positives, increase them.

## Methods

| Method | Description |
|--------|-------------|
| `record_write(table, pk)` | Record a write operation |
| `record_read(table, pk)` | Record a read operation |
| `get_write_count(table, pk)` | Get current write count for a partition |
| `get_read_count(table, pk)` | Get current read count for a partition |
| `set_table_thresholds(table, writes_threshold, reads_threshold)` | Override thresholds for a table |
| `clear()` | Reset all tracked data |

## What to do when you see warnings

Hot partition warnings mean you need to rethink your access pattern:

1. **Spread the load** - Use a more distributed partition key
2. **Add randomness** - Append a random suffix to partition keys
3. **Use write sharding** - Split writes across multiple partitions
4. **Cache reads** - Reduce read pressure with caching
5. **Review your data model** - Maybe the partition key design needs work
