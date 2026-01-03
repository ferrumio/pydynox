# Global Secondary Indexes

GSIs let you query by attributes other than the table's primary key. Define them as class attributes on your Model.

## Define a GSI

```python
from pydynox import Model, ModelConfig, GlobalSecondaryIndex
from pydynox.attributes import StringAttribute, NumberAttribute

class User(Model):
    model_config = ModelConfig(table="users")
    
    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    email = StringAttribute()
    status = StringAttribute()
    age = NumberAttribute()
    
    # GSI with hash key only
    email_index = GlobalSecondaryIndex(
        index_name="email-index",
        hash_key="email",
    )
    
    # GSI with hash and range key
    status_index = GlobalSecondaryIndex(
        index_name="status-index",
        hash_key="status",
        range_key="pk",
    )
```

## Query a GSI

Use the index attribute to query:

```python
# Query by email
users = User.email_index.query(email="john@example.com")
for user in users:
    print(user.name)

# Query by status
active_users = User.status_index.query(status="active")
for user in active_users:
    print(user.email)
```

## Range key conditions

When your GSI has a range key, you can add conditions:

```python
# Query active users with pk starting with "USER#"
users = User.status_index.query(
    status="active",
    range_key_condition=User.pk.begins_with("USER#"),
)

# Query with comparison
users = User.status_index.query(
    status="active",
    range_key_condition=User.pk >= "USER#100",
)
```

## Filter conditions

Filter non-key attributes after the query:

```python
# Query active users over 30
users = User.status_index.query(
    status="active",
    filter_condition=User.age >= 30,
)
```

Note: Filters run after the query. You still pay for RCU on filtered items.

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
# Get results in pages of 10
result = User.status_index.query(status="active", limit=10)

for user in result:
    print(user.email)

# Check if there are more results
if result.last_evaluated_key:
    print("More results available")
```

## Metrics

Access query metrics after iteration:

```python
result = User.email_index.query(email="john@example.com")
users = list(result)

print(f"Duration: {result.metrics.duration_ms}ms")
print(f"RCU consumed: {result.metrics.consumed_rcu}")
```

## Create table with GSI

When creating tables programmatically, include GSI definitions:

```python
client = DynamoDBClient()

client.create_table(
    "users",
    hash_key=("pk", "S"),
    range_key=("sk", "S"),
    global_secondary_indexes=[
        {
            "index_name": "email-index",
            "hash_key": ("email", "S"),
            "projection": "ALL",
        },
        {
            "index_name": "status-index",
            "hash_key": ("status", "S"),
            "range_key": ("pk", "S"),
            "projection": "ALL",
        },
    ],
)
```

## Projection types

Control which attributes are copied to the index:

- `"ALL"` - All attributes (default)
- `"KEYS_ONLY"` - Only key attributes
- `"INCLUDE"` - Specific attributes (use `non_key_attributes`)

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


## Next steps

- [Conditions](conditions.md) - Filter and conditional writes
- [Query](query.md) - Query items by hash key with conditions
- [Tables](tables.md) - Create tables with GSIs
