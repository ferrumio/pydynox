# Models

Models define the structure of your DynamoDB items.

## Key features

- Typed attributes with defaults
- Hash key and range key support
- Required fields with `null=False`
- Convert to/from dict
- TTL (auto-delete items after expiration)

## Getting started

### Basic model

=== "basic_model.py"
    ```python
    --8<-- "docs/examples/models/basic_model.py"
    ```

### Attribute types

| Type | DynamoDB type | Python type |
|------|---------------|-------------|
| `StringAttribute` | S | str |
| `NumberAttribute` | N | int, float |
| `BooleanAttribute` | BOOL | bool |
| `BinaryAttribute` | B | bytes |
| `ListAttribute` | L | list |
| `MapAttribute` | M | dict |
| `TTLAttribute` | N | datetime |

### Keys

Every model needs at least a hash key (partition key):

```python
class User(Model):
    class Meta:
        table = "users"
    
    pk = StringAttribute(hash_key=True)  # Required
```

Add a range key (sort key) for composite keys:

```python
class User(Model):
    class Meta:
        table = "users"
    
    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)  # Optional
```

### Defaults and required fields

=== "with_defaults.py"
    ```python
    --8<-- "docs/examples/models/with_defaults.py"
    ```

## Advanced

### Meta options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `table` | str | Required | DynamoDB table name |
| `region` | str | None | AWS region |
| `endpoint_url` | str | None | Custom endpoint |
| `skip_hooks` | bool | False | Skip lifecycle hooks |

### Converting to dict

```python
user = User(pk="USER#123", sk="PROFILE", name="John")
data = user.to_dict()
# {'pk': 'USER#123', 'sk': 'PROFILE', 'name': 'John'}
```

### Creating from dict

```python
data = {'pk': 'USER#123', 'sk': 'PROFILE', 'name': 'John'}
user = User.from_dict(data)
```

## TTL (Time-To-Live)

Auto-delete items after a certain time. DynamoDB handles the deletion for you - no cron jobs needed.

### What is TTL?

TTL lets you set an expiration time on items. When the time passes, DynamoDB automatically deletes the item. This is useful for:

- **Session data** - Delete sessions after they expire
- **Temporary tokens** - Clean up verification codes, password reset tokens
- **Cache entries** - Remove stale cached data
- **Audit logs** - Keep logs for 90 days, then delete

### Basic TTL usage

Add a `TTLAttribute` to your model and use `ExpiresIn` to set expiration times:

=== "basic_ttl.py"
    ```python
    --8<-- "docs/examples/ttl/basic_ttl.py"
    ```

The `ExpiresIn` helper makes it easy to set expiration times without doing datetime math:

| Method | Description |
|--------|-------------|
| `ExpiresIn.seconds(n)` | n seconds from now |
| `ExpiresIn.minutes(n)` | n minutes from now |
| `ExpiresIn.hours(n)` | n hours from now |
| `ExpiresIn.days(n)` | n days from now |
| `ExpiresIn.weeks(n)` | n weeks from now |

### Checking expiration

You can check if an item has expired without waiting for DynamoDB to delete it:

```python
session = Session.get(pk="SESSION#123")

if session.is_expired:
    print("Session expired, please log in again")
```

Get the time remaining:

```python
remaining = session.expires_in
if remaining:
    print(f"Session expires in {remaining.total_seconds()} seconds")
else:
    print("Session already expired")
```

### Extending TTL

Extend the expiration time for active sessions:

```python
session = Session.get(pk="SESSION#123")
if session and not session.is_expired:
    session.extend_ttl(ExpiresIn.hours(1))  # Add 1 more hour
```

This updates both the local object and DynamoDB.

### Session management example

Here's a complete example of session management with TTL:

=== "session_example.py"
    ```python
    --8<-- "docs/examples/ttl/session_example.py"
    ```

### How DynamoDB TTL works

1. **TTL is stored as epoch timestamp** - The `TTLAttribute` converts datetime to Unix timestamp (seconds since 1970)

2. **Deletion is not instant** - DynamoDB checks TTL every few minutes. Expired items are usually deleted within 48 hours, but often much faster.

3. **You can still read expired items** - Until DynamoDB deletes them, expired items are still in the table. That's why `is_expired` is useful.

4. **Deletions are free** - TTL deletions don't count toward your write capacity. This makes TTL great for cleanup.

5. **Enable TTL on the table** - You need to enable TTL in DynamoDB console or via API. The attribute name must match your `TTLAttribute` field name.

### Enabling TTL on your table

TTL must be enabled on the DynamoDB table. You can do this in the AWS Console:

1. Go to your table in DynamoDB console
2. Click "Additional settings" tab
3. Find "Time to Live (TTL)" section
4. Click "Enable"
5. Enter the attribute name (e.g., `expires_at`)

Or via AWS CLI:

```bash
aws dynamodb update-time-to-live \
    --table-name sessions \
    --time-to-live-specification "Enabled=true, AttributeName=expires_at"
```

!!! warning
    The attribute name in DynamoDB must match your `TTLAttribute` field name exactly. If your model has `expires_at = TTLAttribute()`, use `expires_at` when enabling TTL.

### TTL best practices

1. **Always check `is_expired`** - Don't assume items are deleted immediately after expiration

2. **Use appropriate TTL values** - Too short and you'll have issues; too long and you're storing unnecessary data

3. **Consider time zones** - `ExpiresIn` uses UTC. If your users are in different time zones, be careful with "end of day" logic

4. **Monitor deletions** - DynamoDB publishes TTL deletion metrics to CloudWatch
