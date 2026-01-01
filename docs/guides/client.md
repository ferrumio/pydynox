# DynamoDBClient

The DynamoDBClient is your connection to AWS. Configure it once, use it everywhere.

## Key features

- Multiple credential sources (profile, env vars, explicit)
- Rate limiting built-in
- Local development support (DynamoDB Local, LocalStack)
- Set a default client for all models

## Getting started

### Basic setup

=== "basic_client.py"
    ```python
    --8<-- "docs/examples/client/basic_client.py"
    ```

By default, the client uses the standard AWS credential chain:

1. Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
2. Shared credentials file (`~/.aws/credentials`)
3. Instance profile (EC2, ECS, Lambda)

### Using a profile

=== "client_with_profile.py"
    ```python
    --8<-- "docs/examples/client/client_with_profile.py"
    ```

### Explicit credentials

=== "client_with_credentials.py"
    ```python
    --8<-- "docs/examples/client/client_with_credentials.py"
    ```

!!! warning
    Don't hardcode credentials in your code. Use environment variables or profiles instead.

### Local development

=== "client_local.py"
    ```python
    --8<-- "docs/examples/client/client_local.py"
    ```

## Default client

Instead of passing a client to each model, set a default client once:

=== "default_client.py"
    ```python
    --8<-- "docs/examples/client/default_client.py"
    ```

### How it works

When a model needs a client, it looks in this order:

1. `model_config.client` - if you passed one explicitly
2. Default client - set via `set_default_client()`
3. Error - if neither is set

### Override per model

You can still use a different client for specific models:

```python
# Default for most models
set_default_client(prod_client)

# Different client for audit logs
audit_client = DynamoDBClient(region="eu-west-1")

class AuditLog(Model):
    model_config = ModelConfig(
        table="audit_logs",
        client=audit_client,  # Uses this instead of default
    )
    pk = StringAttribute(hash_key=True)
```

## Rate limiting

Control how fast you hit DynamoDB. Useful to avoid throttling or stay within budget.

=== "client_with_rate_limit.py"
    ```python
    --8<-- "docs/examples/client/client_with_rate_limit.py"
    ```

See the [rate limiting guide](06-rate-limiting.md) for more details.

## Constructor options

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `region` | str | None | AWS region (e.g., "us-east-1") |
| `profile` | str | None | AWS profile name from ~/.aws/credentials |
| `access_key` | str | None | AWS access key ID |
| `secret_key` | str | None | AWS secret access key |
| `session_token` | str | None | AWS session token (for temporary credentials) |
| `endpoint_url` | str | None | Custom endpoint (for local development) |
| `rate_limit` | FixedRate or AdaptiveRate | None | Rate limiter |

## Methods

### ping()

Check if the client can connect to DynamoDB.

```python
if client.ping():
    print("Connected!")
```

### get_region()

Get the configured region.

```python
region = client.get_region()
print(f"Using region: {region}")
```

### Low-level operations

The client has methods for direct DynamoDB operations. Each sync method has an async version with `async_` prefix:

| Sync | Async | Description |
|------|-------|-------------|
| `put_item(table, item)` | `async_put_item(table, item)` | Save an item |
| `get_item(table, key)` | `async_get_item(table, key)` | Get an item by key |
| `delete_item(table, key)` | `async_delete_item(table, key)` | Delete an item |
| `update_item(table, key, updates)` | `async_update_item(table, key, updates)` | Update an item |
| `query(table, key_condition, ...)` | `async_query(table, key_condition, ...)` | Query items |
| `batch_write(table, put_items, delete_keys)` | - | Batch write |
| `batch_get(table, keys)` | - | Batch get |
| `transact_write(operations)` | - | Transaction |

All operations return metrics (duration, RCU/WCU consumed). See [observability](observability.md) for details.

See [async support](async.md) for more details on async operations.

Most of the time you'll use the Model ORM instead of these methods directly.

## Credential priority

When multiple credential sources are available, the client uses this order:

1. Explicit credentials (`access_key`, `secret_key`)
2. Profile (`profile`)
3. Environment variables
4. Default credential chain (instance profile, etc.)

## Tips

- Set `set_default_client()` once at app startup
- Use profiles for local development
- Use instance profiles in production (no credentials in code)
- Add rate limiting if you're doing bulk operations

## boto3 vs pydynox

### What we support today

| Feature | boto3 | pydynox |
|---------|-------|---------|
| Environment variables | ✅ | ✅ |
| AWS profiles | ✅ | ✅ |
| Explicit credentials | ✅ | ✅ |
| Session token | ✅ | ✅ |
| Custom endpoint | ✅ | ✅ |
| Region config | ✅ | ✅ |
| Rate limiting | ❌ | ✅ |

### What's coming

| Feature | boto3 | pydynox | Coming soon |
|---------|-------|---------|-------------|
| Session object | ✅ | ❌ | 🚧 |
| Assume role | ✅ | ❌ | 🚧 |
| STS credentials | ✅ | ❌ | 🚧 |
| Custom retry config | ✅ | ❌ | 🚧 |
| Request/response hooks | ✅ | ❌ | 🚧 |

### Workaround for now

If you need assume role or STS, get temporary credentials outside pydynox and pass them directly:

```python
# Get credentials from STS (using boto3 or AWS CLI)
# Then pass them to pydynox
client = DynamoDBClient(
    access_key=temp_credentials["AccessKeyId"],
    secret_key=temp_credentials["SecretAccessKey"],
    session_token=temp_credentials["SessionToken"],
)
```

### Missing something?

Open a [feature request](https://github.com/leandrodamascena/pydynox/issues/new?template=feature_request.md) on GitHub. We prioritize based on community feedback.
