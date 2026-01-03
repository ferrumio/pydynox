# Query

Query items from DynamoDB using typed conditions. Returns model instances with full type hints.

## Key features

- Type-safe queries with model attributes
- Range key conditions (begins_with, between, comparisons)
- Filter conditions on any attribute
- Automatic pagination
- Ascending/descending sort order
- Async support

## Getting started

### Basic query

Use `Model.query()` to fetch items by hash key:

=== "basic_query.py"
    ```python
    --8<-- "docs/examples/query/basic_query.py"
    ```

The query returns a `ModelQueryResult` that you can:

- Iterate with `for` loop
- Get first result with `.first()`
- Collect all with `list()`

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

### Sorting and limit

Control sort order and page size:

=== "sorting_and_limit.py"
    ```python
    --8<-- "docs/examples/query/sorting_and_limit.py"
    ```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `scan_index_forward` | `True` | `True` = ascending, `False` = descending |
| `limit` | None | Items per page (iterator fetches all pages) |

## Advanced

### Pagination

By default, the iterator fetches all pages automatically. For manual control:

=== "pagination.py"
    ```python
    --8<-- "docs/examples/query/pagination.py"
    ```

Use `last_evaluated_key` to:

- Implement "load more" buttons
- Process large datasets in batches
- Resume interrupted queries

### Consistent reads

For strongly consistent reads:

```python
orders = list(
    Order.query(
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

Access query metrics after iteration:

```python
result = Order.query(hash_key="CUSTOMER#123")
orders = list(result)

print(f"Duration: {result.metrics.duration_ms}ms")
print(f"RCU consumed: {result.metrics.consumed_rcu}")
print(f"Items returned: {result.metrics.items_count}")
```

### Async queries

Use `async_query()` for async code:

=== "async_query.py"
    ```python
    --8<-- "docs/examples/query/async_query.py"
    ```

### Query parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `hash_key` | Any | Required | Hash key value |
| `range_key_condition` | Condition | None | Condition on sort key |
| `filter_condition` | Condition | None | Filter on any attribute |
| `limit` | int | None | Items per page |
| `scan_index_forward` | bool | True | Sort order |
| `consistent_read` | bool | None | Strongly consistent read |
| `last_evaluated_key` | dict | None | Start key for pagination |

## Query vs GSI query

Use `Model.query()` when querying by the table's hash key.

Use [GSI query](indexes.md) when querying by a different attribute:

```python
# Table query - by pk
for order in Order.query(hash_key="CUSTOMER#123"):
    print(order.sk)

# GSI query - by status
for order in Order.status_index.query(status="shipped"):
    print(order.pk)
```

## Next steps

- [Atomic updates](atomic-updates.md) - Increment, append, and other atomic operations
- [Conditions](conditions.md) - All condition operators
- [Indexes](indexes.md) - Query by non-key attributes
