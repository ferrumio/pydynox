# Indexes

DynamoDB supports two types of secondary indexes:

- **Global secondary index (GSI)** - Query by any attribute with a different hash key
- **Local secondary index (LSI)** - Query by the same hash key with a different sort key

## Global secondary indexes

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

### Understanding limit vs page_size

GSI queries support the same pagination parameters as table queries:

| Parameter | What it does | DynamoDB behavior |
|-----------|--------------|-------------------|
| `limit` | Max total items to return | Stops iteration after N items |
| `page_size` | Items per DynamoDB request | Passed as `Limit` to DynamoDB API |

**Key behaviors:**

- `limit=10` → Returns exactly 10 items (or less if fewer match)
- `page_size=50` → Fetches 50 items per request, returns ALL items
- `limit=100, page_size=25` → Returns 100 items, fetching 25 per request (4 requests)

=== "gsi_pagination.py"
    ```python
    --8<-- "docs/examples/indexes/gsi_pagination.py"
    ```

!!! warning "Common mistake"
    If you only set `limit`, it also controls the DynamoDB page size. Use both `limit` and `page_size` when you want to control them separately.

### Manual pagination

For "load more" buttons:

```python
result = User.status_index.query(status="active", limit=10, page_size=10)

for user in result:
    print(user.email)

# Check if there are more results
if result.last_evaluated_key:
    next_result = User.status_index.query(
        status="active",
        limit=10,
        page_size=10,
        last_evaluated_key=result.last_evaluated_key,
    )
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

## GSI limitations

- GSIs are read-only. To update data, update the main table.
- GSI queries are eventually consistent by default.
- Each table can have up to 20 GSIs.
- Multi-attribute keys: max 4 attributes per partition key, 4 per sort key.

---

## Local secondary indexes

LSIs let you query by the same hash key but with a different sort key. They must be created when the table is created and cannot be added later.

### Key features

- Same hash key as the table, different sort key
- Supports strongly consistent reads (unlike GSIs)
- Must be defined at table creation time
- Maximum 5 LSIs per table

### When to use LSI vs GSI

| Feature | LSI | GSI |
|---------|-----|-----|
| Hash key | Same as table | Any attribute |
| Sort key | Different from table | Any attribute |
| Consistent reads | Yes | No |
| Add after table creation | No | Yes |
| Max per table | 5 | 20 |

Use LSI when:

- You need to query by the same hash key with different sort orders
- You need strongly consistent reads on the index
- You know the access patterns at table creation time

### Define an LSI

=== "basic_lsi.py"
    ```python
    --8<-- "docs/examples/indexes/basic_lsi.py"
    ```

### Query an LSI

LSI queries require the hash key (same as the table's hash key):

=== "query_lsi.py"
    ```python
    --8<-- "docs/examples/indexes/query_lsi.py"
    ```

### Consistent reads

LSIs support strongly consistent reads. This is a key difference from GSIs.

=== "lsi_consistent_read.py"
    ```python
    --8<-- "docs/examples/indexes/lsi_consistent_read.py"
    ```

### Pagination

LSI queries support the same pagination parameters as table queries and GSI queries:

| Parameter | What it does | DynamoDB behavior |
|-----------|--------------|-------------------|
| `limit` | Max total items to return | Stops iteration after N items |
| `page_size` | Items per DynamoDB request | Passed as `Limit` to DynamoDB API |

=== "lsi_pagination.py"
    ```python
    --8<-- "docs/examples/indexes/lsi_pagination.py"
    ```

### LSI projections

Like GSIs, LSIs support different projection types:

=== "lsi_with_projection.py"
    ```python
    --8<-- "docs/examples/indexes/lsi_with_projection.py"
    ```

### Create table with LSI

Using `DynamoDBClient`:

=== "create_table_lsi.py"
    ```python
    --8<-- "docs/examples/indexes/create_table_lsi.py"
    ```

Using `Model.create_table()`:

=== "model_create_table_lsi.py"
    ```python
    --8<-- "docs/examples/indexes/model_create_table_lsi.py"
    ```

### LSI limitations

- Must be created with the table (cannot add later)
- Maximum 5 LSIs per table
- Hash key must be the same as the table's hash key
- Table must have a range key to use LSIs

## Next steps

- [Conditions](conditions.md) - Filter and conditional writes
- [Query](query.md) - Query items by hash key with conditions
- [Tables](tables.md) - Create tables with indexes
