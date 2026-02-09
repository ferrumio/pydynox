# Scan and count

Scan reads every item in a DynamoDB table. Use it when you need all items or don't know the partition key.

!!! tip
    For large result sets, you might want to use `as_dict=True`. See [as_dict](#return-dicts-instead-of-models).

## Key features

- Scan all items in a table
- Filter results by any attribute
- Count items without returning them
- Parallel scan for large tables (4-8x faster)
- Automatic pagination
- Async support

## Getting started

pydynox uses an async-first API. Methods without prefix are async (default), methods with `sync_` prefix are sync.

### Basic scan

Use `Model.scan()` to read all items:

=== "Async (default)"
    ```python
    --8<-- "docs/examples/scan/basic_scan.py"
    ```

=== "Sync (use sync_ prefix)"
    ```python
    --8<-- "docs/examples/scan/sync_basic_scan.py"
    ```

The scan returns a result that you can:

- Iterate with `async for` (async) or `for` (sync)
- Get first result with `await .first()` (async) or `.first()` (sync)
- Collect all with `[x async for x in ...]` (async) or `list()` (sync)

### Filter conditions

Filter results by any attribute:

=== "filter_scan.py"
    ```python
    --8<-- "docs/examples/scan/filter_scan.py"
    ```

!!! warning
    Filters run after DynamoDB reads the items. You still pay for reading all items, even if the filter returns fewer.

### Get first result

Get the first matching item:

=== "first_result.py"
    ```python
    --8<-- "docs/examples/scan/first_result.py"
    ```

### Count items

Count items without returning them:

=== "count.py"
    ```python
    --8<-- "docs/examples/scan/count.py"
    ```

!!! note
    Count still scans the entire table. It just doesn't return the items.

## Pagination

### Understanding limit vs page_size

pydynox has two parameters that control pagination:

| Parameter | What it does | DynamoDB behavior |
|-----------|--------------|-------------------|
| `limit` | Max total items to return | Stops iteration after N items |
| `page_size` | Items per DynamoDB request | Passed as `Limit` to DynamoDB API |

This is a common pattern in DynamoDB libraries.

**Key behaviors:**

- `limit=50` → Returns exactly 50 items (or less if table has fewer)
- `page_size=100` → Fetches 100 items per request, returns ALL items
- `limit=500, page_size=100` → Returns 500 items, fetching 100 per request (5 requests)
- Neither set → Returns all items, DynamoDB decides page size

=== "limit_vs_page_size.py"
    ```python
    --8<-- "docs/examples/scan/limit_vs_page_size.py"
    ```

!!! warning "Common mistake"
    If you only set `limit`, it also controls the DynamoDB page size. This means `limit=50` will fetch 50 items per request AND stop after 50 total. If you want to fetch more items per request but still limit the total, use both `limit` and `page_size`.

!!! note "Filters and pagination"
    When using `filter_condition`, remember that `page_size` controls how many items DynamoDB reads per request, not how many items pass the filter. If your filter is very selective, you may need many requests to get enough matching items.

### Automatic pagination

By default, the iterator fetches all pages automatically:

```python
# Async - fetches ALL users, automatically handling pagination
async for user in User.scan():
    print(user.name)

# Sync
for user in User.sync_scan():
    print(user.name)
```

### Manual pagination

For "load more" buttons or batch processing:

```python
# Async
result = User.scan(limit=100, page_size=100)
users = [user async for user in result]

# Get the last key for next page
last_key = result.last_evaluated_key

if last_key:
    next_result = User.scan(
        limit=100,
        page_size=100,
        last_evaluated_key=last_key,
    )

# Sync
result = User.sync_scan(limit=100, page_size=100)
users = list(result)
```

## Advanced

### Why scan is expensive

DynamoDB charges by read capacity units (RCU). Scan reads every item, so you pay for the entire table.

| Table size | Items | RCU (eventually consistent) | RCU (strongly consistent) |
|------------|-------|----------------------------|---------------------------|
| 100 MB | 10,000 | ~25,000 | ~50,000 |
| 1 GB | 100,000 | ~250,000 | ~500,000 |
| 10 GB | 1,000,000 | ~2,500,000 | ~5,000,000 |

Formula:

- Eventually consistent: 1 RCU = 4 KB
- Strongly consistent: 1 RCU = 2 KB (2x cost)

### Parallel scan

For large tables, split the scan across multiple segments to speed it up. Parallel scan runs all segments concurrently using tokio in Rust.

**Performance**: 4 segments = ~4x faster, 8 segments = ~8x faster. RCU cost is the same (you're reading the same data).

=== "Async (default)"
    ```python
    --8<-- "docs/examples/scan/parallel_scan.py"
    ```

=== "Sync (use sync_ prefix)"
    ```python
    # Sync parallel scan
    users, metrics = User.sync_parallel_scan(total_segments=4)
    print(f"Found {len(users)} users in {metrics.duration_ms:.2f}ms")
    ```

**How many segments?**

- Small tables (< 100K items): 1-2 segments
- Medium tables (100K - 1M items): 4-8 segments
- Large tables (> 1M items): 8-16 segments

Experiment to find what works best for your table size.

**Important**: Parallel scan returns all items at once (not paginated). For very large tables that don't fit in memory, use regular `scan()` with segments for streaming:

```python
# Stream items one page at a time (async)
async for user in User.scan(segment=0, total_segments=4):
    process(user)

# Sync
for user in User.sync_scan(segment=0, total_segments=4):
    process(user)
```

### Async and sync usage

Async is the default. Use `async for` to iterate:

```python
# Async scan
async for user in User.scan():
    print(user.name)

# Async count
count, metrics = await User.count()

# Async parallel scan
users, metrics = await User.parallel_scan(total_segments=4)
```

For sync code, use `sync_` prefix:

```python
# Sync scan
for user in User.sync_scan():
    print(user.name)

# Sync count
count, metrics = User.sync_count()

# Sync parallel scan
users, metrics = User.sync_parallel_scan(total_segments=4)
```

### Consistent reads

For strongly consistent reads:

```python
# Async
users = [user async for user in User.scan(consistent_read=True)]

# Sync
users = list(User.sync_scan(consistent_read=True))
```

### Metrics

Access scan metrics using class methods:

```python
result = User.scan()
users = list(result)

# Get last operation metrics
last = User.get_last_metrics()
if last:
    print(f"Duration: {last.duration_ms}ms")
    print(f"RCU consumed: {last.consumed_rcu}")

# Get total metrics
total = User.get_total_metrics()
print(f"Total scans: {total.scan_count}")
```

For more details, see [Observability](observability.md).

### Return dicts instead of models

By default, scan returns Model instances. Each item from DynamoDB is converted to a Python object with all the Model methods and hooks.

This conversion has a cost. Python object creation is slow compared to Rust. For scans that return many items (hundreds or thousands), this becomes a bottleneck.

Use `as_dict=True` to skip Model instantiation and get plain dicts:

=== "as_dict.py"
    ```python
    --8<-- "docs/examples/scan/as_dict.py"
    ```

**When to use `as_dict=True`:**

- Read-only operations where you don't need `.save()`, `.delete()`, or hooks
- Scans returning many items (100+)
- Performance-critical code paths
- Data export or migration scripts

**Trade-offs:**

| | Model instances | `as_dict=True` |
|---|---|---|
| Speed | Slower (Python object creation) | Faster (plain dicts) |
| Methods | `.save()`, `.delete()`, `.update()` | None |
| Hooks | `after_load` runs | No hooks |
| Type hints | Full IDE support | Dict access |
| Validation | Attribute types enforced | Raw DynamoDB types |

!!! note "Why this happens"
    This is how Python works. Creating class instances is expensive. Rust handles the DynamoDB call and deserialization fast, but Python must create each Model object. There's no way around this in Python itself.

### Scan parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `filter_condition` | Condition | None | Filter on any attribute |
| `limit` | int | None | Max total items to return |
| `page_size` | int | None | Items per DynamoDB request |
| `consistent_read` | bool | None | Strongly consistent read |
| `last_evaluated_key` | dict | None | Start key for pagination |
| `segment` | int | None | Segment number for parallel scan |
| `total_segments` | int | None | Total segments for parallel scan |
| `as_dict` | bool | False | Return dicts instead of Model instances |

### Parallel scan parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `total_segments` | int | Required | Number of parallel segments |
| `filter_condition` | Condition | None | Filter on any attribute |
| `consistent_read` | bool | None | Strongly consistent read |
| `as_dict` | bool | False | Return dicts instead of Model instances |

### Count parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `filter_condition` | Condition | None | Filter on any attribute |
| `consistent_read` | bool | None | Strongly consistent read |

## Testing your code

Test scans without DynamoDB using the built-in memory backend:

=== "testing_scan.py"
    ```python
    --8<-- "docs/examples/scan/testing_scan.py"
    ```

No setup needed. Just add `pydynox_memory_backend` to your test function. See [Testing](testing.md) for more details.

## Anti-patterns

### Scan in API endpoints

```python
# Bad: slow and expensive on every request
@app.get("/users")
def list_users():
    return list(User.scan())
```

Use query with a GSI or pagination instead.

### Scan to find one item

```python
# Bad: scanning to find a single user by email
user = User.scan(filter_condition=User.email == "john@example.com").first()
```

Create a GSI on email and use query:

```python
# Good: query on GSI
user = User.email_index.query(partition_key="john@example.com").first()
```

### Expecting filters to reduce cost

```python
# Bad: this still reads all 1 million users
active_users = list(User.scan(filter_condition=User.status == "active"))
```

Use a GSI on status or a different data model.

### Frequent count operations

```python
# Bad: counting on every page load
@app.get("/dashboard")
def dashboard():
    total_users, _ = User.count()
    return {"total": total_users}
```

Maintain a counter in a separate item or use CloudWatch metrics.

## Scan vs query

| | Scan | Query |
|---|---|---|
| Reads | Entire table | Items with same partition key |
| Cost | High (all items) | Low (only matching items) |
| Speed | Slow on large tables | Fast |
| Use case | Export, migration, admin | User-facing, real-time |

If you can use query, use query. Only use scan when you need all items or don't know the partition key.

## Alternatives to scan

| Need | Alternative |
|------|-------------|
| Find by non-key attribute | Create a GSI |
| Count items | Maintain a counter item |
| Search text | Use OpenSearch or Algolia |
| List recent items | GSI with timestamp as sort key |
| Export data | DynamoDB Export to S3 |

## Next steps

- [Query](query.md) - Query by partition key
- [Indexes](indexes.md) - Query by non-key attributes
- [Conditions](conditions.md) - All condition operators
