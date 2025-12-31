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
| `CompressedAttribute` | S | str |

### Keys

Every model needs at least a hash key (partition key):

```python
class User(Model):
    model_config = ModelConfig(table="users")
    
    pk = StringAttribute(hash_key=True)  # Required
```

Add a range key (sort key) for composite keys:

```python
class User(Model):
    model_config = ModelConfig(table="users")
    
    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)  # Optional
```

### Defaults and required fields

=== "with_defaults.py"
    ```python
    --8<-- "docs/examples/models/with_defaults.py"
    ```

## Advanced

### ModelConfig options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `table` | str | Required | DynamoDB table name |
| `client` | DynamoDBClient | None | Client to use (uses default if None) |
| `skip_hooks` | bool | False | Skip lifecycle hooks |
| `max_size` | int | None | Max item size in bytes |

### Setting a default client

Instead of passing a client to each model, set a default client once:

```python
from pydynox import DynamoDBClient, set_default_client

# At app startup
client = DynamoDBClient(region="us-east-1", profile="prod")
set_default_client(client)

# All models use this client
class User(Model):
    model_config = ModelConfig(table="users")
    pk = StringAttribute(hash_key=True)

class Order(Model):
    model_config = ModelConfig(table="orders")
    pk = StringAttribute(hash_key=True)
```

### Override client per model

Use a different client for specific models:

```python
# Default client for most models
set_default_client(prod_client)

# Special client for audit logs
audit_client = DynamoDBClient(region="eu-west-1")

class AuditLog(Model):
    model_config = ModelConfig(
        table="audit_logs",
        client=audit_client,  # Uses different client
    )
    pk = StringAttribute(hash_key=True)
```

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

## Compressed attributes

DynamoDB charges by item size. Large text fields eat up your budget and can hit the 400KB limit. `CompressedAttribute` solves this by compressing large text automatically.

### Why use compression?

- **Save money** - Smaller items = lower storage and I/O costs
- **Avoid limits** - DynamoDB has a 400KB item size limit
- **Transparent** - Compression/decompression happens automatically
- **Fast** - Compression runs in Rust, not Python

### Basic usage

=== "basic_compression.py"
    ```python
    --8<-- "docs/examples/compression/basic_compression.py"
    ```

### Compression algorithms

Three algorithms are available:

| Algorithm | Best for | Trade-off |
|-----------|----------|-----------|
| `Zstd` | Most cases (default) | Best compression ratio |
| `Lz4` | High throughput | Fastest, larger output |
| `Gzip` | Compatibility | Good balance |

=== "algorithm_options.py"
    ```python
    --8<-- "docs/examples/compression/algorithm_options.py"
    ```

### Compression options

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `algorithm` | CompressionAlgorithm | Zstd | Compression algorithm |
| `level` | int | 3 (zstd), 6 (gzip) | Higher = better compression, slower |
| `min_size` | int | 100 | Only compress if >= this many bytes |
| `threshold` | float | 0.9 | Only compress if ratio is below this |

=== "compression_options.py"
    ```python
    --8<-- "docs/examples/compression/compression_options.py"
    ```

### How it works

1. When you save, the attribute checks if the value is large enough (`min_size`)
2. It compresses the data and checks if it's worth it (`threshold`)
3. If compression helps, it stores the compressed data with a prefix like `ZSTD:`
4. When you read, it detects the prefix and decompresses automatically

Small values (under `min_size`) are stored as-is. This avoids overhead for short strings.

### Storage format

Compressed values are stored as base64-encoded strings with a prefix:

- `ZSTD:abc123...` - Zstd compressed
- `LZ4:abc123...` - LZ4 compressed  
- `GZIP:abc123...` - Gzip compressed

Values without a prefix are stored uncompressed.

!!! tip
    You can change the algorithm later. Old items will still decompress correctly because the prefix tells pydynox which algorithm was used.

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
