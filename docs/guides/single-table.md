# Single-table design

Single-table design is a DynamoDB pattern where you store multiple entity types in one table. Instead of having separate tables for Users, Orders, and Products, you put them all in the same table and use key prefixes to distinguish them.

## Why single-table?

DynamoDB charges per table and has limits on how many tables you can create. More importantly, single-table design lets you fetch related data in one query. In a multi-table design, getting a user and their orders requires two separate API calls. With single-table, you can get both in one query.

The tradeoff is complexity. You need to carefully design your keys to support all your access patterns. pydynox makes this easier with template keys.

!!! tip "Learn more"
    Alex DeBrie's [The What, Why, and When of Single-Table Design](https://www.alexdebrie.com/posts/dynamodb-single-table/) is the best introduction to this pattern.

## The problem

Without templates, you manually build keys and can make mistakes:

```python
class User(Model):
    model_config = ModelConfig(table="app")
    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)

class Order(Model):
    model_config = ModelConfig(table="app")
    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)

# Bug: Order with User's key pattern - no error!
Order(pk="USER#john@example.com", sk="PROFILE")
```

There's no validation. You can accidentally create an Order with a User's key pattern and corrupt your data.

## Template keys

Add `template` to `StringAttribute` to define key patterns:

=== "template_basic.py"
    ```python
    --8<-- "docs/examples/single_table/template_basic.py"
    ```

The template `USER#{email}` means: take the `email` attribute value and put it after `USER#`. The `{email}` part is a placeholder that gets replaced with the actual value.

Static templates like `PROFILE` have no placeholders - they're always the same value.

## Multiple placeholders

Templates can have multiple placeholders:

=== "template_multiple.py"
    ```python
    --8<-- "docs/examples/single_table/template_multiple.py"
    ```

This is useful when you need to sort by multiple attributes. Here, orders are sorted by order_id first, then by date.

## Querying with templates

Query using placeholder names instead of building keys manually:

```python
# Without template - you build the key yourself
async for order in Order.query(partition_key="USER#123"):
    print(order)

# With template - pass the placeholder value
async for order in Order.query(user_id="123"):
    print(order)
```

Both work. The template version is cleaner and less error-prone. pydynox builds `USER#123` for you.

## Inverted indexes

This is where single-table design gets powerful.

Imagine you have users and orders. You want to:

1. Get all orders for a user (query by user_id)
2. Find which user made a specific order (query by order_id)

With a regular table, you can only query by the hash key (user_id). To query by order_id, you need a Global Secondary Index (GSI) that "inverts" the keys - the sort key becomes the hash key.

=== "inverted_index.py"
    ```python
    --8<-- "docs/examples/single_table/inverted_index.py"
    ```

The GSI query also uses template placeholders. You pass `order_id="003"` and pydynox builds `ORDER#003` for the GSI hash key.

## Follower/following pattern

A classic social media pattern. You want to answer two questions:

1. Who does Alice follow?
2. Who follows Bob?

=== "follower_following.py"
    ```python
    --8<-- "docs/examples/single_table/follower_following.py"
    ```

One table, one GSI, two access patterns.

## Mixed entity types

Multiple models can share the same table. This is the core of single-table design:

=== "mixed_entities.py"
    ```python
    --8<-- "docs/examples/single_table/mixed_entities.py"
    ```

The `begins_with("ORDER#")` filter is important. Without it, the query would also return the user's profile (which has the same pk but sk="PROFILE").

## Collection - multi-entity query

When you have multiple entity types under the same partition key, you often want to fetch them all in one query. `Collection` does this for you.

Instead of:

```python
user = await User.get(pk="USER#123", sk="PROFILE")
orders = [o async for o in Order.query(pk="USER#123")]
# = 2 DynamoDB calls
```

Use Collection:

```python
from pydynox import Collection

collection = Collection([User, Order, Address])
result = await collection.query(pk="USER#123")
# = 1 DynamoDB call

result.users      # [User(...)]
result.orders     # [Order(...), Order(...)]
result.addresses  # [Address(...)]
```

### Requirements

All models in a Collection must:

1. Share the same table
2. Have a discriminator field (`_type = StringAttribute(discriminator=True)`)

The discriminator tells pydynox which model class to use when deserializing each item.

### Basic usage

=== "basic.py"
    ```python
    --8<-- "docs/examples/collection/basic.py"
    ```

### Filter by sort key

Use `sk_begins_with` to filter results:

=== "sk_filter.py"
    ```python
    --8<-- "docs/examples/collection/sk_filter.py"
    ```

### With inheritance

Collection works well with model inheritance:

=== "with_inheritance.py"
    ```python
    --8<-- "docs/examples/collection/with_inheritance.py"
    ```

### Typed results

Results are fully typed. IDE autocomplete works:

```python
result = await collection.query(pk="USER#123")

# IDE knows these are User and Order instances
user: User = result.users[0]
order: Order = result.orders[0]

# Autocomplete works
print(user.name)    # User.name
print(order.total)  # Order.total
```

### Sync version

Use `sync_query` for synchronous code:

```python
result = collection.sync_query(pk="USER#123")
```

## Best practices

| Practice | Why |
|----------|-----|
| Use clear prefixes | `USER#`, `ORDER#`, `PROFILE` make debugging easier |
| Match placeholder names to attributes | `template="USER#{user_id}"` with `user_id = StringAttribute()` |
| Filter by sk prefix | When querying mixed entities with same pk |
| Create GSI at table creation | Adding GSIs later requires a migration |
| Use discriminator for Collection | Required for multi-entity queries |

## Testing your code

Use `MemoryBackend` as a pytest fixture to test template keys without DynamoDB:

=== "testing_template.py"
    ```python
    --8<-- "docs/examples/single_table/testing_template.py"
    ```

## Table creation

Create the table with the inverted GSI:

```python
from pydynox import DynamoDBClient

client = DynamoDBClient()

await client.create_table(
    "app",
    partition_key=("pk", "S"),
    sort_key=("sk", "S"),
    global_secondary_indexes=[
        {
            "index_name": "inverted",
            "partition_key": ("sk", "S"),
            "sort_key": ("pk", "S"),
            "projection": "ALL",
        },
    ],
)
```

## Further reading

- [Alex DeBrie - Single-Table Design](https://www.alexdebrie.com/posts/dynamodb-single-table/) - The definitive guide
- [AWS - Best practices for DynamoDB](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/bp-general-nosql-design.html) - Official AWS guidance
- [The DynamoDB Book](https://www.dynamodbbook.com/) - Deep dive into DynamoDB patterns

## Next steps

- [Indexes](indexes.md) - Learn more about GSI and LSI
- [Query](query.md) - Query patterns and pagination
- [Conditions](conditions.md) - Conditional writes and filters
- [Testing](testing.md) - Testing with MemoryBackend
