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

## Environment variables

pydynox uses the [AWS SDK for Rust](https://docs.aws.amazon.com/sdk-for-rust/latest/dg/environment-variables.html), which supports standard AWS environment variables:

| Variable | Description |
|----------|-------------|
| `AWS_ACCESS_KEY_ID` | Access key for authentication |
| `AWS_SECRET_ACCESS_KEY` | Secret key for authentication |
| `AWS_SESSION_TOKEN` | Session token for temporary credentials |
| `AWS_REGION` / `AWS_DEFAULT_REGION` | Default region |
| `AWS_PROFILE` | Profile name from `~/.aws/credentials` |
| `AWS_ENDPOINT_URL` | Custom endpoint (for local dev) |
| `AWS_MAX_ATTEMPTS` | Max retry attempts |
| `AWS_RETRY_MODE` | Retry mode: `standard` or `adaptive` |

These work automatically - no code changes needed. Set them in your shell, `.env` file, or CI/CD pipeline.

```bash
export AWS_REGION=us-east-1
export AWS_PROFILE=my-profile
```

For the full list, see the [AWS SDK environment variables documentation](https://docs.aws.amazon.com/sdk-for-rust/latest/dg/environment-variables.html).

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
    pk = StringAttribute(partition_key=True)
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

### Table operations

Table operations follow the async-first pattern. Async methods have no prefix, sync methods have `sync_` prefix.

| Async (default) | Sync | Description |
|-----------------|------|-------------|
| `create_table(...)` | `sync_create_table(...)` | Create a new table |
| `table_exists(table)` | `sync_table_exists(table)` | Check if table exists |
| `delete_table(table)` | `sync_delete_table(table)` | Delete a table |
| `wait_for_table_active(table)` | `sync_wait_for_table_active(table)` | Wait for table to be ready |

See [table operations](tables.md) for details.

### Item operations

Item operations also follow async-first. Async methods have no prefix, sync methods have `sync_` prefix.

| Async (default) | Sync | Description |
|-----------------|------|-------------|
| `put_item(table, item, ...)` | `sync_put_item(...)` | Save an item. Overwrites if key exists. |
| `get_item(table, key)` | `sync_get_item(...)` | Get item by primary key. |
| `delete_item(table, key, ...)` | `sync_delete_item(...)` | Delete item by primary key. |
| `update_item(table, key, updates, ...)` | `sync_update_item(...)` | Update specific attributes. |
| `query(table, key_condition, ...)` | `sync_query(...)` | Find items by partition key. |
| `batch_write(table, put_items, delete_keys)` | `sync_batch_write(...)` | Write up to 25 items at once. |
| `batch_get(table, keys)` | `sync_batch_get(...)` | Get up to 100 items at once. |
| `transact_write(operations)` | `sync_transact_write(...)` | Atomic multi-item write. |
| `transact_get(gets)` | `sync_transact_get(...)` | Atomic multi-item read. |

Write methods (`put_item`, `update_item`, `delete_item`) support these optional parameters:

| Parameter | Description |
|-----------|-------------|
| `condition_expression` | Condition that must be true for the write to succeed |
| `expression_attribute_names` | Placeholders for reserved words |
| `expression_attribute_values` | Placeholders for values |
| `return_values_on_condition_check_failure` | If `True`, get the existing item on `ConditionalCheckFailedException` |

### Utility methods

| Method | Description |
|--------|-------------|
| `ping()` | Check if the client can connect to DynamoDB. Returns `True` or `False`. |
| `get_region()` | Get the AWS region this client is configured for. |

See [async operations](async.md) for examples and best practices.

## Next steps

- [Models](models.md) - Define models with typed attributes
- [Rate limiting](rate-limiting.md) - Control throughput
- [Async](async.md) - Async operations
