# Query

Query items from DynamoDB using typed conditions. Returns model instances with full type hints.

!!! tip
    For large result sets, you might want to use `as_dict=True`. See [as_dict](#return-dicts-instead-of-models).

## Key features

- Type-safe queries with model attributes
- Range key conditions (begins_with, between, comparisons)
- Filter conditions on any attribute
- Automatic pagination
- Ascending/descending sort order
- Async support

## Getting started

pydynox uses an async-first API. Methods without prefix are async (default), methods with `sync_` prefix are sync.

### Basic query

Use `Model.query()` to fetch items by hash key:

=== "Async (default)"
    ```python
    --8<-- "docs/examples/query/basic_query.py"
    ```

=== "Sync (use sync_ prefix)"
    ```python
    --8<-- "docs/examples/query/sync_basic_query.py"
    ```

The query returns a result that you can:

- Iterate with `async for` (async) or `for` (sync)
- Get first result with `await .first()` (async) or `.first()` (sync)
- Collect all with `[x async for x in ...]` (async) or `list()` (sync)

### Range key conditions

Filter by sort key using attribute conditions:

=== "range_key_condition.py"
    ```python
    --8<-- "docs/examples/query/range_key_condition.py"
    ```

Available range key conditions:

| Condition | Example | Description |
|-----------|---------|-------------|
| `begins_with` | `Order.sk.begins_with("ORDER#")` | Sort key starts with prefix |
| `between` | `Order.sk.between("A", "Z")` | Sort key in range |
| `=` | `Order.sk == "ORDER#001"` | Exact match |
| `<` | `Order.sk < "ORDER#100"` | Less than |
| `<=` | `Order.sk <= "ORDER#100"` | Less than or equal |
| `>` | `Order.sk > "ORDER#001"` | Greater than |
| `>=` | `Order.sk >= "ORDER#001"` | Greater than or equal |

!!! tip
    Range key conditions are efficient. DynamoDB uses them to limit the items it reads.

### Filter conditions

Filter results by any attribute:

=== "filter_condition.py"
    ```python
    --8<-- "docs/examples/query/filter_condition.py"
    ```

!!! warning
    Filter conditions are applied after DynamoDB reads the items. You still pay for the read capacity of filtered-out items.

### Sorting

Control sort order:

=== "sorting_and_limit.py"
    ```python
    --8<-- "docs/examples/query/sorting_and_limit.py"
    ```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `scan_index_forward` | `True` | `True` = ascending, `False` = descending |

## Pagination

### Understanding limit vs page_size

pydynox has two parameters that control pagination:

| Parameter | What it does | DynamoDB behavior |
|-----------|--------------|-------------------|
| `limit` | Max total items to return | Stops iteration after N items |
| `page_size` | Items per DynamoDB request | Passed as `Limit` to DynamoDB API |

This is a common pattern in DynamoDB libraries.

**Key behaviors:**

- `limit=10` → Returns exactly 10 items (or less if table has fewer)
- `page_size=25` → Fetches 25 items per request, returns ALL items
- `limit=100, page_size=25` → Returns 100 items, fetching 25 per request (4 requests)
- Neither set → Returns all items, DynamoDB decides page size

=== "limit_vs_page_size.py"
    ```python
    --8<-- "docs/examples/query/limit_vs_page_size.py"
    ```

!!! warning "Common mistake"
    If you only set `limit`, it also controls the DynamoDB page size. This means `limit=10` will fetch 10 items per request AND stop after 10 total. If you want to fetch more items per request but still limit the total, use both `limit` and `page_size`.

### Automatic pagination

By default, the iterator fetches all pages automatically:

```python
# Async - fetches ALL orders, automatically handling pagination
async for order in Order.query(hash_key="CUSTOMER#123"):
    print(order.sk)

# Sync
for order in Order.sync_query(hash_key="CUSTOMER#123"):
    print(order.sk)
```

### Manual pagination

For "load more" buttons or batch processing, use `last_evaluated_key`:

=== "pagination.py"
    ```python
    --8<-- "docs/examples/query/pagination.py"
    ```

Use `last_evaluated_key` to:

- Implement "load more" buttons
- Process large datasets in batches
- Resume interrupted queries

## Advanced

### Consistent reads

For strongly consistent reads:

```python
# Async
orders = [
    order
    async for order in Order.query(
        hash_key="CUSTOMER#123",
        consistent_read=True,
    )
]

# Sync
orders = list(
    Order.sync_query(
        hash_key="CUSTOMER#123",
        consistent_read=True,
    )
)
```

Or set it as default in ModelConfig:

```python
class Order(Model):
    model_config = ModelConfig(table="orders", consistent_read=True)
```

### Metrics

Access query metrics using class methods:

```python
result = Order.query(hash_key="CUSTOMER#123")
orders = list(result)

# Get last operation metrics
last = Order.get_last_metrics()
if last:
    print(f"Duration: {last.duration_ms}ms")
    print(f"RCU consumed: {last.consumed_rcu}")

# Get total metrics across all operations
total = Order.get_total_metrics()
print(f"Total RCU: {total.total_rcu}")
```

For more details, see [Observability](observability.md).

### Async queries

Async is the default. Use `async for` to iterate:

```python
async for order in Order.query(hash_key="CUSTOMER#123"):
    print(order.sk)

# Get first
first = await Order.query(hash_key="CUSTOMER#123").first()

# Collect all
orders = [order async for order in Order.query(hash_key="CUSTOMER#123")]
```

### Sync queries

Use `sync_query()` for sync code:

```python
for order in Order.sync_query(hash_key="CUSTOMER#123"):
    print(order.sk)

# Get first
first = Order.sync_query(hash_key="CUSTOMER#123").first()

# Collect all
orders = list(Order.sync_query(hash_key="CUSTOMER#123"))
```

### Return dicts instead of models

By default, query returns Model instances. Each item from DynamoDB is converted to a Python object with all the Model methods and hooks.

This conversion has a cost. Python object creation is slow compared to Rust. For queries that return many items (hundreds or thousands), this becomes a bottleneck.

Use `as_dict=True` to skip Model instantiation and get plain dicts:

=== "as_dict.py"
    ```python
    --8<-- "docs/examples/query/as_dict.py"
    ```

**When to use `as_dict=True`:**

- Read-only operations where you don't need `.save()`, `.delete()`, or hooks
- Queries returning many items (100+)
- Performance-critical code paths
- Data export or transformation pipelines

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

### Query parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `hash_key` | Any | Required | Hash key value |
| `range_key_condition` | Condition | None | Condition on sort key |
| `filter_condition` | Condition | None | Filter on any attribute |
| `limit` | int | None | Max total items to return |
| `page_size` | int | None | Items per DynamoDB request |
| `scan_index_forward` | bool | True | Sort order |
| `consistent_read` | bool | None | Strongly consistent read |
| `last_evaluated_key` | dict | None | Start key for pagination |
| `as_dict` | bool | False | Return dicts instead of Model instances |

## Query vs GSI query

Use `Model.query()` when querying by the table's hash key.

Use [GSI query](indexes.md) when querying by a different attribute:

```python
# Table query - by pk (async)
async for order in Order.query(hash_key="CUSTOMER#123"):
    print(order.sk)

# GSI query - by status (async)
async for order in Order.status_index.query(status="shipped"):
    print(order.pk)

# Sync versions
for order in Order.sync_query(hash_key="CUSTOMER#123"):
    print(order.sk)

for order in Order.status_index.sync_query(status="shipped"):
    print(order.pk)
```

## Testing your code

Test queries without DynamoDB using the built-in memory backend:

=== "testing_query.py"
    ```python
    --8<-- "docs/examples/query/testing_query.py"
    ```

No setup needed. Just add `pydynox_memory_backend` to your test function. See [Testing](testing.md) for more details.

## Next steps

- [Atomic updates](atomic-updates.md) - Increment, append, and other atomic operations
- [Conditions](conditions.md) - All condition operators
- [Indexes](indexes.md) - Query by non-key attributes
