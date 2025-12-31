# Exceptions

pydynox maps AWS SDK errors to Python exceptions. This makes error handling easier and more Pythonic.

## Key features

- Clear exception hierarchy
- Helpful error messages
- Maps AWS errors to specific types
- Base exception for catch-all handling

## Getting started

### Exception hierarchy

All pydynox exceptions inherit from `PydynoxError`. You can catch specific errors or use the base class:

| Exception | When it happens |
|-----------|-----------------|
| `PydynoxError` | Base exception for all pydynox errors |
| `TableNotFoundError` | Table does not exist |
| `TableAlreadyExistsError` | Table already exists |
| `ValidationError` | Invalid input (bad key, wrong type, etc.) |
| `ConditionCheckFailedError` | Condition expression returned false |
| `TransactionCanceledError` | Transaction failed |
| `ThrottlingError` | Request rate too high |
| `AccessDeniedError` | IAM permission denied |
| `CredentialsError` | AWS credentials missing or invalid |
| `SerializationError` | Cannot convert data to/from DynamoDB format |
| `ConnectionError` | Cannot connect to DynamoDB |
| `EncryptionError` | KMS encryption/decryption failed |

### Basic error handling

Import exceptions from `pydynox.pydynox_core`:

=== "handling_errors.py"
    ```python
    --8<-- "docs/examples/exceptions/handling_errors.py"
    ```

### Condition check errors

When using conditional writes, catch `ConditionCheckFailedError`:

=== "condition_check.py"
    ```python
    --8<-- "docs/examples/exceptions/condition_check.py"
    ```

## Advanced

### Connection errors

`ConnectionError` happens when pydynox cannot reach DynamoDB. Common causes:

- DynamoDB Local is not running
- Wrong endpoint URL
- Network issues
- Firewall blocking the connection

```python
from pydynox.pydynox_core import ConnectionError

try:
    client = DynamoDBClient(endpoint_url="http://localhost:8000")
    client.ping()
except ConnectionError:
    print("Start DynamoDB Local first: docker run -p 8000:8000 amazon/dynamodb-local")
```

### Credential errors

`CredentialsError` happens when AWS credentials are missing or invalid:

```python
from pydynox.pydynox_core import CredentialsError

try:
    client = DynamoDBClient()
    client.ping()
except CredentialsError as e:
    print(f"Fix your credentials: {e}")
```

Common causes:
- No AWS credentials configured
- Invalid access key or secret key
- Expired session token
- Wrong AWS profile name

### Throttling errors

`ThrottlingError` happens when you exceed your table's capacity:

```python
from pydynox.pydynox_core import ThrottlingError
import time

def save_with_retry(client, table, item, max_retries=3):
    for attempt in range(max_retries):
        try:
            client.put_item(table, item)
            return
        except ThrottlingError:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                time.sleep(wait_time)
            else:
                raise
```

!!! tip
    Use the built-in rate limiting feature instead of manual retry logic. See the Rate limiting guide.

### Transaction errors

`TransactionCanceledError` includes details about why the transaction failed:

```python
from pydynox import Transaction
from pydynox.exceptions import TransactionCanceledError

try:
    with Transaction() as tx:
        tx.put("accounts", {"pk": "ACC#1", "balance": 100})
        tx.update(
            "accounts",
            {"pk": "ACC#2"},
            updates={"balance": 200},
            condition_expression="attribute_exists(pk)",
        )
except TransactionCanceledError as e:
    print(f"Transaction failed: {e}")
    # e.g., "Transaction was canceled: Condition check failed"
```

### Encryption errors

`EncryptionError` happens when KMS encryption or decryption fails:

```python
from pydynox.exceptions import EncryptionError

try:
    user.save()  # Has an EncryptedAttribute
except EncryptionError as e:
    print(f"Encryption failed: {e}")
```

Common causes:

- KMS key not found (wrong key ID or alias)
- KMS key is disabled
- Missing IAM permissions for `kms:Encrypt` or `kms:Decrypt`
- Wrong encryption context on decrypt
- Invalid ciphertext (data corrupted)

### Best practices

1. **Catch specific exceptions first** - Put specific handlers before the base `PydynoxError`

2. **Log the full error** - Exception messages include useful details from AWS

3. **Use retry for throttling** - Or better, use rate limiting to avoid throttling

4. **Check credentials early** - Call `client.ping()` at startup to catch credential issues

5. **Handle connection errors gracefully** - Especially in Lambda where cold starts can cause timeouts
