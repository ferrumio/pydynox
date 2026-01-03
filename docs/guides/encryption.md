# Field encryption

Encrypt sensitive fields like SSN or credit cards using AWS KMS.

## Key features

- Per-field encryption with KMS
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

If you try to decrypt in `WriteOnly` mode, you get an `EncryptionError`. Same for encrypting in `ReadOnly` mode.

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

1. On save, the attribute calls KMS `Encrypt` with your plaintext
2. KMS returns ciphertext encrypted with your key
3. The ciphertext is base64-encoded and stored with `ENC:` prefix
4. On read, the attribute detects the prefix and calls KMS `Decrypt`
5. KMS returns the original plaintext

All encryption happens in Rust for speed. The KMS client is created lazily on first use.

### Storage format

Encrypted values are stored as:

```
ENC:<base64-encoded-ciphertext>
```

Values without the `ENC:` prefix are treated as plaintext. This means you can add encryption to existing fields - old unencrypted values still work.

## Limitations

- **AWS credentials from environment** - Uses the default credential chain (env vars, IAM role, etc.). You cannot pass credentials directly.
- **Region from environment** - Uses `AWS_REGION` or `AWS_DEFAULT_REGION` env var by default. You can override with the `region` parameter.
- **Strings only** - Only encrypts string values. For other types, convert to string first.
- **No key rotation** - If you rotate your KMS key, old data still decrypts (KMS handles this), but you need to re-encrypt to use the new key.

## IAM permissions

Your service needs these KMS permissions:

```json
{
    "Effect": "Allow",
    "Action": [
        "kms:Encrypt",
        "kms:Decrypt"
    ],
    "Resource": "arn:aws:kms:us-east-1:123456789:key/your-key-id"
}
```

For `WriteOnly` mode, you only need `kms:Encrypt`. For `ReadOnly`, only `kms:Decrypt`.

## Error handling

Encryption errors raise `EncryptionError`:

```python
from pydynox.exceptions import EncryptionError

try:
    user.save()
except EncryptionError as e:
    print(f"Encryption failed: {e}")
```

Common errors:

| Error | Cause |
|-------|-------|
| KMS key not found | Wrong key ID or alias |
| Access denied | Missing IAM permissions |
| Cannot encrypt in ReadOnly mode | Wrong mode for operation |
| Cannot decrypt in WriteOnly mode | Wrong mode for operation |


## Next steps

- [Size calculator](size-calculator.md) - Check item sizes
- [IAM permissions](iam-permissions.md) - KMS permissions
- [Attributes](attributes.md) - All attribute types
