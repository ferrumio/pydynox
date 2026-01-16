# Global secondary indexes

GSIs let you query by attributes other than the table's primary key. Define them as class attributes on your Model.

## Key features

- Query by any attribute, not just the primary key
- Single or multi-attribute composite keys (up to 4 per key)
- Range key conditions for efficient filtering
- Automatic pagination with metrics

## Define a GSI

=== "basic_gsi.py"
    ```python
    --8<-- "docs/examples/indexes/basic_gsi.py"
    ```

## Query a GSI

Use the index attribute to query:

=== "query_gsi.py"
    ```python
    --8<-- "docs/examples/indexes/query_gsi.py"
    ```

## Range key conditions

When your GSI has a range key, you can add conditions:

=== "range_key_condition.py"
    ```python
    --8<-- "docs/examples/indexes/range_key_condition.py"
    ```

## Filter conditions

Filter non-key attributes after the query:

=== "filter_condition.py"
    ```python
    --8<-- "docs/examples/indexes/filter_condition.py"
    ```

!!! warning
    Filters run after the query. You still pay for RCU on filtered items.

## Sort order

Control the sort order with `scan_index_forward`:

```python
# Ascending (default)
users = User.status_index.query(status="active", scan_index_forward=True)

# Descending
users = User.status_index.query(status="active", scan_index_forward=False)
```

## Pagination

Use `limit` to control page size:

```python
result = User.status_index.query(status="active", limit=10)

for user in result:
    print(user.email)

# Check if there are more results
if result.last_evaluated_key:
    print("More results available")
```

## Async queries

Use `async_query` for async/await support:

```python
async for user in User.email_index.async_query(email="john@example.com"):
    print(user.name)

# With filter
async for user in User.status_index.async_query(
    status="active",
    filter_condition=User.age >= 18,
):
    print(user.email)

# Get first result
user = await User.email_index.async_query(email="john@example.com").first()
```

## Metrics

Access query metrics using class methods:

```python
result = User.email_index.query(email="john@example.com")
users = list(result)

# Get last operation metrics
last = User.get_last_metrics()
if last:
    print(f"Duration: {last.duration_ms}ms")
    print(f"RCU consumed: {last.consumed_rcu}")
```

For more details, see [Observability](observability.md).

## Multi-attribute composite keys

DynamoDB supports up to 4 attributes per partition key and 4 per sort key in GSIs. This is useful for multi-tenant apps or complex access patterns.

=== "multi_attr_gsi.py"
    ```python
    --8<-- "docs/examples/indexes/multi_attr_gsi.py"
    ```

### Query multi-attribute GSI

All partition key attributes are required. Sort key attributes are optional.

=== "query_multi_attr.py"
    ```python
    --8<-- "docs/examples/indexes/query_multi_attr.py"
    ```

### When to use multi-attribute keys

| Use case | Example |
|----------|---------|
| Multi-tenant apps | `hash_key=["tenant_id", "entity_type"]` |
| Hierarchical data | `hash_key=["country", "state"]` |
| Time-series | `range_key=["year", "month", "day"]` |
| Composite sorting | `range_key=["priority", "created_at"]` |

!!! tip
    Multi-attribute keys avoid the need to create synthetic composite keys like `tenant_id#region`. DynamoDB handles the composition for you.

## Create table with GSI

When creating tables programmatically, include GSI definitions:

=== "create_table_gsi.py"
    ```python
    --8<-- "docs/examples/indexes/create_table_gsi.py"
    ```

### Multi-attribute GSI in create_table

Use `hash_keys` and `range_keys` (plural) for multi-attribute keys:

=== "create_table_multi_attr.py"
    ```python
    --8<-- "docs/examples/indexes/create_table_multi_attr.py"
    ```

## Projection types

Control which attributes are copied to the index:

| Projection | Description | Use when |
|------------|-------------|----------|
| `"ALL"` | All attributes (default) | You need all data from the index |
| `"KEYS_ONLY"` | Only key attributes | You just need to check existence |
| `"INCLUDE"` | Specific attributes | You need some attributes, not all |

```python
# Keys only - smallest index, lowest cost
{
    "index_name": "status-index",
    "hash_key": ("status", "S"),
    "projection": "KEYS_ONLY",
}

# Include specific attributes
{
    "index_name": "email-index",
    "hash_key": ("email", "S"),
    "projection": "INCLUDE",
    "non_key_attributes": ["name", "created_at"],
}
```

## Limitations

- GSIs are read-only. To update data, update the main table.
- GSI queries are eventually consistent by default.
- Each table can have up to 20 GSIs.
- Multi-attribute keys: max 4 attributes per partition key, 4 per sort key.

## Next steps

- [Conditions](conditions.md) - Filter and conditional writes
- [Query](query.md) - Query items by hash key with conditions
- [Tables](tables.md) - Create tables with GSIs
