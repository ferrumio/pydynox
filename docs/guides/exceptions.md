# Exceptions

pydynox maps AWS SDK errors to Python exceptions. This makes error handling easier and more Pythonic.

## Key features

- Clear exception hierarchy
- Helpful error messages
- Maps AWS errors to specific types
- Base exception for catch-all handling

## Getting started

### Exception hierarchy

All pydynox exceptions inherit from `PydynoxException`. You can catch specific errors or use the base class:

| Exception | When it happens |
|-----------|-----------------|
| `PydynoxException` | Base exception for all pydynox errors |
| `ResourceNotFoundException` | Table does not exist |
| `ResourceInUseException` | Table already exists |
| `ValidationException` | Invalid input (bad key, wrong type, etc.) |
| `ConditionalCheckFailedException` | Condition expression returned false |
| `TransactionCanceledException` | Transaction failed |
| `ProvisionedThroughputExceededException` | Request rate too high |
| `AccessDeniedException` | IAM permission denied |
| `CredentialsException` | AWS credentials missing or invalid |
| `SerializationException` | Cannot convert data to/from DynamoDB format |
| `ConnectionException` | Cannot connect to DynamoDB |
| `EncryptionException` | KMS encryption/decryption failed |
| `S3AttributeException` | S3 upload/download failed |
| `ItemTooLargeException` | Item exceeds max_size limit (Python-only) |

### Basic error handling

Import exceptions from `pydynox.pydynox_core`:

=== "handling_errors.py"
    ```python
    --8<-- "docs/examples/exceptions/handling_errors.py"
    ```

### Condition check errors

When using conditional writes, catch `ConditionalCheckFailedException`:

=== "condition_check.py"
    ```python
    --8<-- "docs/examples/exceptions/condition_check.py"
    ```

### Get the item that caused the failure

When a condition fails, you often need to see what's in DynamoDB. Instead of making an extra GET call, use `return_values_on_condition_check_failure=True`. The existing item is attached to the exception:

=== "return_item_on_failure.py"
    ```python
    --8<-- "docs/examples/exceptions/return_item_on_failure.py"
    ```

This works with `put_item`, `update_item`, and `delete_item`. The `item` attribute is `None` if you don't set the flag.

## Advanced

### Connection errors

`ConnectionException` happens when pydynox cannot reach DynamoDB. Common causes:

- DynamoDB Local is not running
- Wrong endpoint URL
- Network issues
- Firewall blocking the connection

```python
from pydynox.pydynox_core import ConnectionException

try:
    client = DynamoDBClient(endpoint_url="http://localhost:8000")
    client.ping()
except ConnectionException:
    print("Start DynamoDB Local first: docker run -p 8000:8000 amazon/dynamodb-local")
```

### Credential errors

`CredentialsException` happens when AWS credentials are missing or invalid:

```python
from pydynox.pydynox_core import CredentialsException

try:
    client = DynamoDBClient()
    client.ping()
except CredentialsException as e:
    print(f"Fix your credentials: {e}")
```

Common causes:
- No AWS credentials configured
- Invalid access key or secret key
- Expired session token
- Wrong AWS profile name

### Throttling errors

`ProvisionedThroughputExceededException` happens when you exceed your table's capacity:

```python
from pydynox.pydynox_core import ProvisionedThroughputExceededException
import time

def save_with_retry(client, table, item, max_retries=3):
    for attempt in range(max_retries):
        try:
            client.put_item(table, item)
            return
        except ProvisionedThroughputExceededException:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                time.sleep(wait_time)
            else:
                raise
```

!!! tip
    Use the built-in rate limiting feature instead of manual retry logic. See the Rate limiting guide.

### Transaction errors

`TransactionCanceledException` includes details about why the transaction failed:

```python
from pydynox import Transaction
from pydynox.exceptions import TransactionCanceledException

try:
    with Transaction() as tx:
        tx.put("accounts", {"pk": "ACC#1", "balance": 100})
        tx.update(
            "accounts",
            {"pk": "ACC#2"},
            updates={"balance": 200},
            condition_expression="attribute_exists(pk)",
        )
except TransactionCanceledException as e:
    print(f"Transaction failed: {e}")
    # e.g., "Transaction was canceled: Condition check failed"
```

### Encryption errors

`EncryptionException` happens when KMS encryption or decryption fails:

```python
from pydynox.exceptions import EncryptionException

try:
    user.save()  # Has an EncryptedAttribute
except EncryptionException as e:
    print(f"Encryption failed: {e}")
```

Common causes:

- KMS key not found (wrong key ID or alias)
- KMS key is disabled
- Missing IAM permissions for `kms:GenerateDataKey` or `kms:Decrypt`
- Wrong encryption context on decrypt
- Invalid ciphertext (data corrupted)

### Best practices

1. **Catch specific exceptions first** - Put specific handlers before the base `PydynoxException`

2. **Log the full error** - Exception messages include useful details from AWS

3. **Use retry for throttling** - Or better, use rate limiting to avoid throttling

4. **Check credentials early** - Call `client.ping()` at startup to catch credential issues

5. **Handle connection errors gracefully** - Especially in Lambda where cold starts can cause timeouts


## Next steps

- [IAM permissions](iam-permissions.md) - Required AWS permissions
- [Rate limiting](rate-limiting.md) - Avoid throttling errors
- [Observability](observability.md) - Logging and metrics
