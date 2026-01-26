# Field encryption

Protect sensitive data like SSN, credit cards, or API keys at rest. pydynox encrypts fields before saving to DynamoDB and decrypts them when reading back. Uses AWS KMS for key management.

## Key features

- Per-field encryption with KMS envelope encryption
- No size limit (works with fields up to 400KB)
- Three modes: ReadWrite, WriteOnly, ReadOnly
- Encryption context for extra security
- Automatic encrypt on save, decrypt on load

## Getting started

### Basic usage

Add `EncryptedAttribute` to fields that need encryption:

=== "basic_encryption.py"
    ```python
    --8<-- "docs/examples/encryption/basic_encryption.py"
    ```

The field is encrypted before saving to DynamoDB. When you read it back, it's decrypted automatically. In DynamoDB, the value looks like `ENC:base64data...`.

### Encryption modes

Not all services need both encrypt and decrypt. A service that only writes data shouldn't be able to read it back. Use modes to control this:

| Mode | Can encrypt | Can decrypt | Use case |
|------|-------------|-------------|----------|
| `ReadWrite` | ✓ | ✓ | Full access (default) |
| `WriteOnly` | ✓ | ✗ (returns encrypted) | Ingest services |
| `ReadOnly` | ✗ (returns plaintext) | ✓ | Report services |

Import `EncryptionMode` from `pydynox.attributes`:

=== "encryption_modes.py"
    ```python
    --8<-- "docs/examples/encryption/encryption_modes.py"
    ```

If you try to decrypt in `WriteOnly` mode, you get an `EncryptionException`. Same for encrypting in `ReadOnly` mode.

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `key_id` | str | Required | KMS key ID, ARN, or alias |
| `mode` | EncryptionMode | ReadWrite | Controls encrypt/decrypt access |
| `region` | str | None | AWS region (uses env default) |
| `context` | dict | None | Encryption context for extra security |

## Advanced

### Encryption context

KMS supports encryption context - extra key-value pairs that must match on decrypt. If someone tries to decrypt with a different context, it fails.

=== "encryption_context.py"
    ```python
    --8<-- "docs/examples/encryption/encryption_context.py"
    ```

This is useful for:

- **Multi-tenant apps** - Include tenant ID in context
- **Audit** - Context is logged in CloudTrail
- **Extra validation** - Ensure data is decrypted in the right context

### How it works

pydynox uses envelope encryption for field-level encryption:

**Encrypt:**

1. Call `KMS:GenerateDataKey` once to get a plaintext key + encrypted key
2. Use the plaintext key to AES-256-GCM encrypt locally (fast, in Rust)
3. Pack the encrypted key + encrypted data together
4. Base64 encode and add `ENC:` prefix

**Decrypt:**

1. Decode base64 and unpack the envelope
2. Call `KMS:Decrypt` on the encrypted key to get plaintext key
3. Use the plaintext key to AES-256-GCM decrypt locally

This approach has two big advantages over direct KMS Encrypt/Decrypt:

- **No 4KB limit** - KMS Encrypt only accepts 4KB, but DynamoDB fields can be 400KB
- **Fewer KMS calls** - One call per operation instead of one per field

### Storage format

Encrypted values are stored as:

```
ENC:<base64-encoded-envelope>
```

The envelope contains:
- Version byte (for future compatibility)
- Encrypted data key length (2 bytes)
- Encrypted data key (from KMS)
- Encrypted data (AES-256-GCM with random nonce)

Values without the `ENC:` prefix are treated as plaintext. This means you can add encryption to existing fields - old unencrypted values still work.

## Limitations

- **Inherits credentials from DynamoDBClient** - Uses the same AWS credentials configured in your `DynamoDBClient`. No need to configure separately.
- **Strings only** - Only encrypts string values. For other types, convert to string first.
- **No key rotation** - If you rotate your KMS key, old data still decrypts (KMS handles this), but you need to re-encrypt to use the new key.

## IAM permissions

Your service needs these KMS permissions:

```json
{
    "Effect": "Allow",
    "Action": [
        "kms:GenerateDataKey",
        "kms:Decrypt"
    ],
    "Resource": "arn:aws:kms:us-east-1:123456789:key/your-key-id"
}
```

Note: We use `kms:GenerateDataKey` instead of `kms:Encrypt`. For `ReadOnly` mode, you only need `kms:Decrypt`.

## Error handling

Encryption errors raise `EncryptionException`:

```python
from pydynox.exceptions import EncryptionException

try:
    user.save()
except EncryptionException as e:
    print(f"Encryption failed: {e}")
```

Common errors:

| Error | Cause |
|-------|-------|
| KMS key not found | Wrong key ID or alias |
| Access denied | Missing IAM permissions |
| Cannot encrypt in ReadOnly mode | Wrong mode for operation |
| Cannot decrypt in WriteOnly mode | Wrong mode for operation |
| Decryption failed | Data corrupted or wrong key |


## Next steps

- [Size calculator](size-calculator.md) - Check item sizes
- [IAM permissions](iam-permissions.md) - KMS permissions
- [Attributes](attributes.md) - All attribute types
