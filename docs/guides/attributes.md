# Attribute types

Attributes define the fields in your model. Each attribute maps to a DynamoDB type.

## Overview

| Type | DynamoDB | Python | Use case |
|------|----------|--------|----------|
| `StringAttribute` | S | str | Text, IDs, keys |
| `NumberAttribute` | N | int, float | Counts, prices |
| `BooleanAttribute` | BOOL | bool | Flags |
| `BinaryAttribute` | B | bytes | Files, images |
| `ListAttribute` | L | list | Ordered items |
| `MapAttribute` | M | dict | Nested objects |
| `JSONAttribute` | S | dict, list | Complex JSON |
| `EnumAttribute` | S | Enum | Status, types |
| `DatetimeAttribute` | S | datetime | Timestamps (ISO) |
| `TTLAttribute` | N | datetime | Auto-expiring items |
| `StringSetAttribute` | SS | set[str] | Unique strings |
| `NumberSetAttribute` | NS | set[int\|float] | Unique numbers |
| `CompressedAttribute` | S | str | Large text |
| `EncryptedAttribute` | S | str | Sensitive data |
| `S3Attribute` | M | S3Value | Large files in S3 |

## Common parameters

All attributes share these parameters:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `hash_key` | bool | False | Is this the partition key |
| `range_key` | bool | False | Is this the sort key |
| `default` | Any | None | Default value or `AutoGenerate` strategy |
| `required` | bool | False | Field must have a value (not None) |

!!! tip
    Use `AutoGenerate` strategies for automatic ID and timestamp generation. See [Auto-generate strategies](auto-generate.md).

## Basic types

### StringAttribute

Store text values. Most common attribute type.

```python
from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute

class User(Model):
    model_config = ModelConfig(table="users")
    
    pk = StringAttribute(hash_key=True)
    name = StringAttribute()
    email = StringAttribute(required=True)  # Required
```

### NumberAttribute

Store integers and floats. DynamoDB stores all numbers as strings internally.

```python
from pydynox.attributes import NumberAttribute

class Product(Model):
    model_config = ModelConfig(table="products")
    
    pk = StringAttribute(hash_key=True)
    price = NumberAttribute()
    quantity = NumberAttribute(default=0)
```

### BooleanAttribute

Store true/false values.

```python
from pydynox.attributes import BooleanAttribute

class User(Model):
    model_config = ModelConfig(table="users")
    
    pk = StringAttribute(hash_key=True)
    is_active = BooleanAttribute(default=True)
    is_verified = BooleanAttribute(default=False)
```

### BinaryAttribute

Store raw bytes. Useful for small files or binary data.

```python
from pydynox.attributes import BinaryAttribute

class Document(Model):
    model_config = ModelConfig(table="documents")
    
    pk = StringAttribute(hash_key=True)
    thumbnail = BinaryAttribute()
```

### ListAttribute

Store ordered lists. Can contain mixed types.

```python
from pydynox.attributes import ListAttribute

class Post(Model):
    model_config = ModelConfig(table="posts")
    
    pk = StringAttribute(hash_key=True)
    tags = ListAttribute(default=[])
    comments = ListAttribute()
```

### MapAttribute

Store nested objects as DynamoDB's native Map type.

```python
from pydynox.attributes import MapAttribute

class User(Model):
    model_config = ModelConfig(table="users")
    
    pk = StringAttribute(hash_key=True)
    address = MapAttribute()

user = User(
    pk="USER#1",
    address={"street": "123 Main St", "city": "NYC", "zip": "10001"}
)
```

## JSON and enum types

### JSONAttribute

Store dict or list as a JSON string. Different from `MapAttribute`:

- `MapAttribute` uses DynamoDB's native Map type
- `JSONAttribute` stores as a string (useful for complex nested structures)

=== "json_attribute.py"
    ```python
    --8<-- "docs/examples/models/json_attribute.py"
    ```

When to use `JSONAttribute` over `MapAttribute`:

- Deep nesting (DynamoDB has limits on nested maps)
- You need to store the exact JSON structure
- Compatibility with other systems expecting JSON

### EnumAttribute

Store Python enum as its value. Keeps your code type-safe.

=== "enum_attribute.py"
    ```python
    --8<-- "docs/examples/models/enum_attribute.py"
    ```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `enum_class` | type[Enum] | Required | The Enum class |

## Date and time types

### DatetimeAttribute

Store datetime as ISO 8601 string. Sortable as string, good for range queries.

=== "datetime_attribute.py"
    ```python
    --8<-- "docs/examples/models/datetime_attribute.py"
    ```

Naive datetimes (without timezone) are treated as UTC.

### TTLAttribute

Store datetime as epoch timestamp for DynamoDB's auto-delete feature.

```python
from pydynox.attributes import TTLAttribute, ExpiresIn

class Session(Model):
    model_config = ModelConfig(table="sessions")
    
    pk = StringAttribute(hash_key=True)
    expires_at = TTLAttribute()

# Create session that expires in 1 hour
session = Session(pk="SESSION#123", expires_at=ExpiresIn.hours(1))
await session.save()
```

`ExpiresIn` helpers:

| Method | Description |
|--------|-------------|
| `ExpiresIn.seconds(n)` | n seconds from now |
| `ExpiresIn.minutes(n)` | n minutes from now |
| `ExpiresIn.hours(n)` | n hours from now |
| `ExpiresIn.days(n)` | n days from now |
| `ExpiresIn.weeks(n)` | n weeks from now |

Models with `TTLAttribute` also get:

- `is_expired` - check if item expired
- `expires_in` - get time remaining as timedelta
- `extend_ttl()` - extend expiration and save

!!! tip
    See [TTL guide](ttl.md) for full documentation on expiration checking, extending TTL, and best practices.

!!! warning
    TTL must be enabled on the DynamoDB table. The attribute name must match exactly.

## Set types

### StringSetAttribute

Store unique strings. DynamoDB native set type (SS).

```python
from pydynox.attributes import StringSetAttribute

class User(Model):
    model_config = ModelConfig(table="users")
    
    pk = StringAttribute(hash_key=True)
    roles = StringSetAttribute()

user = User(pk="USER#1", roles={"admin", "editor"})
await user.save()

# Check membership
print("admin" in user.roles)  # True
```

### NumberSetAttribute

Store unique numbers. DynamoDB native set type (NS).

=== "set_attributes.py"
    ```python
    --8<-- "docs/examples/models/set_attributes.py"
    ```

!!! note
    Empty sets are stored as None. On load, you get an empty Python set.

## Special types

### CompressedAttribute

Auto-compress large text. Saves storage costs and avoids the 400KB limit.

```python
from pydynox.attributes import CompressedAttribute, CompressionAlgorithm

class Document(Model):
    model_config = ModelConfig(table="documents")
    
    pk = StringAttribute(hash_key=True)
    body = CompressedAttribute()  # Uses zstd by default
    logs = CompressedAttribute(algorithm=CompressionAlgorithm.Lz4)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `algorithm` | CompressionAlgorithm | Zstd | Compression algorithm |
| `level` | int | 3 | Compression level |
| `min_size` | int | 100 | Min bytes to compress |
| `threshold` | float | 0.9 | Only compress if ratio below this |

Algorithms:

| Algorithm | Best for |
|-----------|----------|
| `Zstd` | Most cases (default) |
| `Lz4` | Speed over size |
| `Gzip` | Compatibility |

### EncryptedAttribute

Encrypt sensitive data using AWS KMS.

```python
from pydynox.attributes import EncryptedAttribute, EncryptionMode

class User(Model):
    model_config = ModelConfig(table="users")
    
    pk = StringAttribute(hash_key=True)
    ssn = EncryptedAttribute(key_id="alias/my-key")
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `key_id` | str | Required | KMS key ID or alias |
| `mode` | EncryptionMode | ReadWrite | ReadWrite, WriteOnly, or ReadOnly |
| `region` | str | None | AWS region |
| `context` | dict | None | Encryption context |

Modes:

| Mode | Encrypt | Decrypt | Use case |
|------|---------|---------|----------|
| `ReadWrite` | ✓ | ✓ | Full access |
| `WriteOnly` | ✓ | ✗ | Ingest service |
| `ReadOnly` | ✗ | ✓ | Report service |

!!! tip
    See [Encryption guide](encryption.md) for full documentation on modes, encryption context, and how it works.

### S3Attribute

Store large files in S3 with metadata in DynamoDB. Use when files exceed DynamoDB's 400KB limit.

=== "basic_upload.py"
    ```python
    --8<-- "docs/examples/s3/basic_upload.py"
    ```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `bucket` | str | Required | S3 bucket name |
| `prefix` | str | "" | Key prefix for files |
| `region` | str | None | S3 region (inherits from client) |

After upload, access file metadata:

| Property | Type | Description |
|----------|------|-------------|
| `bucket` | str | S3 bucket name |
| `key` | str | S3 object key |
| `size` | int | File size in bytes |
| `etag` | str | S3 ETag |
| `content_type` | str | MIME type |
| `last_modified` | str | Last modified timestamp |
| `version_id` | str | S3 version ID |
| `metadata` | dict | User-defined metadata |

Download methods:

| Method | Description |
|--------|-------------|
| `get_bytes()` | Download to memory |
| `save_to(path)` | Stream to file |
| `presigned_url(expires)` | Get presigned URL |

!!! tip
    See [S3 attribute guide](s3-attribute.md) for full documentation.

## Choosing the right type

| Need | Use |
|------|-----|
| Simple text | `StringAttribute` |
| Numbers | `NumberAttribute` |
| True/false | `BooleanAttribute` |
| Nested object | `MapAttribute` |
| Complex JSON | `JSONAttribute` |
| Type-safe status | `EnumAttribute` |
| Sortable timestamp | `DatetimeAttribute` |
| Auto-expiring items | `TTLAttribute` |
| Unique values | `StringSetAttribute` / `NumberSetAttribute` |
| Large text | `CompressedAttribute` |
| Sensitive data | `EncryptedAttribute` |
| Large files | `S3Attribute` |


## Next steps

- [Indexes](indexes.md) - Query by non-key attributes with GSIs
- [Auto-generate](auto-generate.md) - Generate IDs and timestamps
- [Encryption](encryption.md) - Field-level encryption with KMS
- [S3 attribute](s3-attribute.md) - Store large files in S3
