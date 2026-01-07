# ADR 012: Envelope encryption with KMS GenerateDataKey

## Status

Accepted (implemented in v0.14.0)

## Context

The current encryption calls `KMS:Encrypt` and `KMS:Decrypt` for each field. This has two problems:

1. **4KB limit** - KMS Encrypt only accepts up to 4KB, but a DynamoDB field can be up to 400KB
2. **Too many calls** - Batch write with 30 items × 3 encrypted fields = 90 KMS calls. Slow and expensive.

## Decision

Use envelope encryption with `KMS:GenerateDataKey`.

### How it works

**Encrypt:**
1. Call `KMS:GenerateDataKey` once → get plaintext key + encrypted key
2. Use plaintext key to AES-256-GCM encrypt locally (Rust, fast)
3. Store encrypted data + encrypted key in DynamoDB

**Decrypt:**
1. Read encrypted data + encrypted key from DynamoDB
2. Call `KMS:Decrypt` on the encrypted key → get plaintext key
3. Use plaintext key to AES-256-GCM decrypt locally (Rust, fast)

### Storage format

```
┌─────────────────────────────────────────────────┐
│ ENC: | encrypted_dek (base64) | nonce | ciphertext │
└─────────────────────────────────────────────────┘
```

The `ENC:` prefix identifies encrypted values.

### Python API

The `EncryptedAttribute` provides field-level encryption:

```python
from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute, EncryptedAttribute, EncryptionMode

class User(Model):
    model_config = ModelConfig(table="users")
    pk = StringAttribute(hash_key=True)
    
    # Full access (default) - can encrypt and decrypt
    ssn = EncryptedAttribute(key_id="alias/my-key")
    
    # Write-only - can encrypt, fails on decrypt
    credit_card = EncryptedAttribute(
        key_id="alias/my-key",
        mode=EncryptionMode.WriteOnly,
    )
    
    # Read-only - can decrypt, fails on encrypt
    legacy_data = EncryptedAttribute(
        key_id="alias/my-key",
        mode=EncryptionMode.ReadOnly,
    )
```

**EncryptionMode options:**
- `ReadWrite` (default): Can encrypt and decrypt
- `WriteOnly`: Can only encrypt (useful for ingest services)
- `ReadOnly`: Can only decrypt (useful for report services)

**Optional parameters:**
- `region`: AWS region (uses default if not set)
- `context`: Encryption context dict for extra security

## Reasons

1. **No size limit** - AES encryption in Rust has no size limit. Fields up to 400KB work fine.

2. **Fewer KMS calls** - One `GenerateDataKey` per batch instead of one per field. 90 calls → 1 call.

3. **Faster** - AES-256-GCM in Rust is much faster than KMS API calls over the network.

4. **Cheaper** - KMS charges per API call. Fewer calls = lower cost.

5. **Standard pattern** - Envelope encryption is the recommended pattern by AWS.

6. **Flexible access control** - EncryptionMode allows separation of encrypt/decrypt permissions.

## Alternatives considered

- **Keep current approach** - Does not work for fields > 4KB
- **Chunk large fields** - Complex, error-prone, still many KMS calls
- **Client-side keys only** - No KMS integration, users manage keys themselves

## Consequences

- Fields of any size (up to 400KB) can be encrypted
- Batch operations are much faster
- Lower KMS costs
- Encrypted data format changes (migration needed for existing data)
- Data key can be reused within a batch for better performance
- Services can have different access levels (write-only ingest, read-only reports)
