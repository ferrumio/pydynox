# ADR 016: Unified AWS Client Configuration

## Status

Accepted

## Context

pydynox uses three AWS services: DynamoDB, S3 (for large attributes), and KMS (for encryption). Before this change, each client was created separately with its own:

1. **Tokio runtime** - Each client created its own async runtime
2. **Credential resolution** - Each client resolved credentials independently
3. **Configuration code** - Duplicated logic for region, endpoint, timeouts, retries

This caused three problems:

### Problem 1: Overhead

Creating a Tokio runtime is not free. Each runtime spawns threads and allocates memory. With three separate runtimes (DynamoDB, S3, KMS), we had:

- 3x thread pool overhead
- 3x memory allocation
- Potential deadlocks on Windows when multiple runtimes exist

### Problem 2: Non-unified errors

Each client had its own error mapping. The same error (e.g., connection refused) could produce different messages:

```
DynamoDB: "Connection failed"
S3: "Failed to connect to S3"
KMS: "KMS connection error"
```

This made debugging harder and the library felt inconsistent.

### Problem 3: Duplicated code

The credential resolution logic was copy-pasted across three files:

- `client.rs` - DynamoDB credentials
- `s3/client.rs` - S3 credentials (same logic)
- `kms/client.rs` - KMS credentials (same logic)

Any bug fix or feature (like adding SSO support) had to be done three times.

## Decision

Unify all AWS client configuration into a shared module.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DynamoDBClient                           │
│                                                             │
│   - client: DynamoDB client (always created)                │
│   - runtime: Arc<Runtime> (shared global)                   │
│   - config: Arc<AwsConfig> (shared)                         │
│   - s3_client: OnceCell<S3Client> (lazy)                    │
│   - kms_client: OnceCell<KmsClient> (lazy)                  │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ shares
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    client_internal/                         │
│                                                             │
│   config.rs   - AwsConfig struct (region, creds, timeouts)  │
│   auth.rs     - Credential providers (static, profile, etc) │
│   builder.rs  - build_dynamodb_client(), build_s3_client(), │
│                 build_kms_client()                          │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ uses
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Global RUNTIME                           │
│                                                             │
│   static RUNTIME: Lazy<Arc<Runtime>>                        │
│   - Single Tokio runtime for all AWS operations             │
│   - Shared by DynamoDB, S3, KMS                             │
└─────────────────────────────────────────────────────────────┘
```

### Key changes

1. **Single global runtime** - All AWS clients share one Tokio runtime via `Arc<Runtime>`

2. **Shared AwsConfig** - One struct holds all config (region, credentials, timeouts). Created once by `DynamoDBClient`, shared with S3/KMS.

3. **Lazy client creation** - S3 and KMS clients are created only when needed (first S3Attribute or EncryptedAttribute operation). Uses `OnceCell` for thread-safe lazy init.

4. **Unified error mapping** - Single `map_common_error()` function handles connection, credential, and access errors for all services. Service-specific errors are handled by `map_sdk_error()`, `map_s3_error()`, `map_kms_error()`.

### Error message format

All connection errors now follow the same pattern:

```
"Connection failed to DynamoDB. Check if the endpoint is reachable."
"Connection failed to S3. Check if the endpoint is reachable."
"Connection failed to KMS. Check if the endpoint is reachable."
```

The service name is injected, making it clear which service failed.

## Performance impact

### Memory

Before: 3 Tokio runtimes × ~2MB each = ~6MB overhead
After: 1 Tokio runtime = ~2MB overhead

**Savings: ~4MB**

### Cold start (Lambda)

Before: 3 credential resolutions (profile loading, STS calls for AssumeRole)
After: 1 credential resolution, reused by all clients

**Savings: 100-300ms** (depends on credential type)

### Lazy initialization

S3 and KMS clients are only created when needed:

- If you never use `S3Attribute`, no S3 client is created
- If you never use `EncryptedAttribute`, no KMS client is created

This means most users (who only use DynamoDB) pay zero overhead for S3/KMS.

## Alternatives considered

### Keep separate clients

Pros: Simpler code, no shared state
Cons: All three problems remain (overhead, inconsistent errors, duplication)

### Expose S3Client and KmsClient to users

Pros: More flexibility
Cons: Breaks encapsulation, users don't need direct access to these clients

We decided that S3 and KMS are internal implementation details. Users interact with `S3Attribute` and `EncryptedAttribute`, not with raw clients.

## Consequences

### Positive

- Lower memory usage (single runtime)
- Faster cold starts (single credential resolution)
- Consistent error messages across all services
- Single place to fix bugs or add features
- S3/KMS only initialized when needed

### Negative

- More complex internal architecture
- Shared state requires careful thread safety (solved with `Arc` and `OnceCell`)
- All services share the same endpoint override (usually what you want for local testing)

## Files changed

- `src/client_internal/config.rs` - New: AwsConfig struct
- `src/client_internal/auth.rs` - New: Credential providers
- `src/client_internal/builder.rs` - New: Client builders
- `src/client.rs` - Updated: Uses shared config, lazy S3/KMS
- `src/s3/client.rs` - Updated: Uses AwsConfig
- `src/kms/client.rs` - Updated: Uses AwsConfig
- `src/errors.rs` - Updated: Unified error mapping with AwsService enum
