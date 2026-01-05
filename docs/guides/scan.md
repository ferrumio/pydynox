# Scan and count

Scan reads every item in a DynamoDB table. Use it when you need all items or don't know the partition key.

## Key features

- Scan all items in a table
- Filter results by any attribute
- Count items without returning them
- Parallel scan for large tables
- Automatic pagination
- Async support

## Getting started

### Basic scan

Use `Model.scan()` to read all items:

=== "basic_scan.py"
    ```python
    --8<-- "docs/examples/scan/basic_scan.py"
    ```

The scan returns a `ModelScanResult` that you can:

- Iterate with `for` loop
- Get first result with `.first()`
- Collect all with `list()`

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

Split the scan across multiple workers to speed up large tables:

=== "parallel_scan.py"
    ```python
    --8<-- "docs/examples/scan/parallel_scan.py"
    ```

Parallel scan is faster but uses the same total RCU. It spreads the work across multiple threads.

### Async scan

Use `async_scan()` and `async_count()` for async code:

=== "async_scan.py"
    ```python
    --8<-- "docs/examples/scan/async_scan.py"
    ```

### Pagination

By default, the iterator fetches all pages automatically. For manual control:

```python
result = User.scan(limit=100)
users = list(result)

# Get the last key for next page
last_key = result.last_evaluated_key

if last_key:
    next_result = User.scan(limit=100, last_evaluated_key=last_key)
```

### Consistent reads

For strongly consistent reads:

```python
users = list(User.scan(consistent_read=True))
```

### Metrics

Access scan metrics after iteration:

```python
result = User.scan()
users = list(result)

print(f"Duration: {result.metrics.duration_ms}ms")
print(f"Items returned: {result.metrics.items_count}")
print(f"Items scanned: {result.metrics.scanned_count}")
print(f"RCU consumed: {result.metrics.consumed_rcu}")
```

### Scan parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `filter_condition` | Condition | None | Filter on any attribute |
| `limit` | int | None | Items per page |
| `consistent_read` | bool | None | Strongly consistent read |
| `last_evaluated_key` | dict | None | Start key for pagination |
| `segment` | int | None | Segment number for parallel scan |
| `total_segments` | int | None | Total segments for parallel scan |

### Count parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `filter_condition` | Condition | None | Filter on any attribute |
| `consistent_read` | bool | None | Strongly consistent read |

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
user = User.email_index.query(email="john@example.com").first()
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
