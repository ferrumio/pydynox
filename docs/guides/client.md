# DynamoDBClient

The DynamoDBClient is the connection between your code and DynamoDB. It handles authentication, network calls, retries, and timeouts.

## Why use it?

pydynox Models need a client to talk to DynamoDB. You can either:

1. Set a default client once at app startup (recommended)
2. Pass a client to each model's config

The client wraps the AWS SDK and adds features like rate limiting. It's built in Rust for speed.

## Key features

- Multiple credential sources (env vars, profile, SSO, AssumeRole)
- Timeout and retry configuration
- Rate limiting built-in
- Local development support

## Basic usage

=== "basic_client.py"
    ```python
    --8<-- "docs/examples/client/basic_client.py"
    ```

By default, the client uses the AWS credential chain: env vars, profile, instance profile, EKS IRSA, etc.

## Credentials

pydynox supports multiple ways to authenticate. Pick the one that fits your environment.

### Environment variables

Set `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`. The client picks them up automatically. Good for local dev and CI/CD.

### Profile (including SSO)

Use a named profile from `~/.aws/credentials` or `~/.aws/config`. Works with SSO profiles too. Good for local dev with multiple AWS accounts.

=== "client_with_profile.py"
    ```python
    --8<-- "docs/examples/client/client_with_profile.py"
    ```

For SSO profiles, run `aws sso login --profile my-profile` first.

### AssumeRole

Assume an IAM role in another account. Good for cross-account access or when you need temporary elevated permissions.

=== "client_assume_role.py"
    ```python
    --8<-- "docs/examples/client/client_assume_role.py"
    ```

### Explicit credentials

Pass credentials directly. Good for testing or when credentials come from a secrets manager. Avoid hardcoding in production.

=== "client_with_credentials.py"
    ```python
    --8<-- "docs/examples/client/client_with_credentials.py"
    ```

!!! warning
    Don't hardcode credentials. Use env vars or profiles instead.

### EKS IRSA / GitHub Actions OIDC

These work automatically via the default credential chain. The env vars are injected by EKS or GitHub Actions. Just use `DynamoDBClient()` with no config. Good for Kubernetes and CI/CD pipelines.

## Configuration

### Timeouts and retries

=== "client_timeouts.py"
    ```python
    --8<-- "docs/examples/client/client_timeouts.py"
    ```

=== "client_retries.py"
    ```python
    --8<-- "docs/examples/client/client_retries.py"
    ```

### Local development

=== "client_local.py"
    ```python
    --8<-- "docs/examples/client/client_local.py"
    ```

### Proxy

=== "client_proxy.py"
    ```python
    --8<-- "docs/examples/client/client_proxy.py"
    ```

## Default client

Set a default client once instead of passing it to each model:

=== "default_client.py"
    ```python
    --8<-- "docs/examples/client/default_client.py"
    ```

Override per model if needed:

```python
set_default_client(prod_client)

# Different client for audit logs
class AuditLog(Model):
    model_config = ModelConfig(table="audit_logs", client=audit_client)
    pk = StringAttribute(hash_key=True)
```

## Rate limiting

=== "client_with_rate_limit.py"
    ```python
    --8<-- "docs/examples/client/client_with_rate_limit.py"
    ```

See [rate limiting](rate-limiting.md) for details.

## Constructor reference

| Parameter | Type | Description |
|-----------|------|-------------|
| `region` | str | AWS region |
| `profile` | str | AWS profile name (supports SSO) |
| `access_key` | str | AWS access key ID |
| `secret_key` | str | AWS secret access key |
| `session_token` | str | Session token for temporary credentials |
| `endpoint_url` | str | Custom endpoint for local dev |
| `role_arn` | str | IAM role ARN for AssumeRole |
| `role_session_name` | str | Session name for AssumeRole |
| `external_id` | str | External ID for AssumeRole |
| `connect_timeout` | float | Connection timeout (seconds) |
| `read_timeout` | float | Read timeout (seconds) |
| `max_retries` | int | Max retry attempts |
| `proxy_url` | str | HTTP/HTTPS proxy URL |
| `rate_limit` | FixedRate/AdaptiveRate | Rate limiter |

## Methods

Most of the time you'll use Models instead of these methods directly. But they're useful for quick operations or when you need more control.

### Sync methods

| Method | Description |
|--------|-------------|
| `ping()` | Check if the client can connect to DynamoDB. Returns `True` or `False`. |
| `get_region()` | Get the AWS region this client is configured for. |
| `put_item(table, item, ...)` | Save an item to a table. Overwrites if the key exists. |
| `get_item(table, key)` | Get a single item by its primary key. Returns `None` if not found. |
| `delete_item(table, key, ...)` | Delete an item by its primary key. |
| `update_item(table, key, updates, ...)` | Update specific attributes without replacing the whole item. |
| `query(table, key_condition, ...)` | Find items by partition key. Supports filtering and pagination. |
| `batch_write(table, put_items, delete_keys)` | Write up to 25 items in one request. Faster than individual puts. |
| `batch_get(table, keys)` | Get up to 100 items in one request. Faster than individual gets. |
| `transact_write(operations)` | Write multiple items atomically. All succeed or all fail. |
| `transact_get(gets)` | Read multiple items atomically. Consistent snapshot. |

Write methods (`put_item`, `update_item`, `delete_item`) support these optional parameters:

| Parameter | Description |
|-----------|-------------|
| `condition_expression` | Condition that must be true for the write to succeed |
| `expression_attribute_names` | Placeholders for reserved words |
| `expression_attribute_values` | Placeholders for values |
| `return_values_on_condition_check_failure` | If `True`, get the existing item on `ConditionalCheckFailedException` |

### Async methods

| Method | Description |
|--------|-------------|
| `async_put_item(table, item)` | Async version of put_item. |
| `async_get_item(table, key)` | Async version of get_item. |
| `async_delete_item(table, key)` | Async version of delete_item. |
| `async_update_item(table, key, updates)` | Async version of update_item. |
| `async_query(table, key_condition, ...)` | Async version of query. |
| `async_transact_write(operations)` | Async version of transact_write. |
| `async_transact_get(gets)` | Async version of transact_get. |

See [async operations](async.md) for examples and best practices.

## Next steps

- [Models](models.md) - Define models with typed attributes
- [Rate limiting](rate-limiting.md) - Control throughput
- [Async](async.md) - Async operations
