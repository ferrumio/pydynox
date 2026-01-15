# Operations metrics

Track KMS and S3 API calls alongside your DynamoDB operations. When you use encryption or large object storage, pydynox measures the time and calls to these services.

## Why track operations metrics

DynamoDB metrics alone don't tell the full story. If you use:

- **EncryptedAttribute** - KMS calls add latency and cost
- **S3Attribute** - S3 uploads/downloads add latency and data transfer costs

Without tracking these, you might wonder why a "simple save" takes 200ms when DynamoDB only took 10ms.

## KMS metrics

When you use `EncryptedAttribute`, pydynox calls AWS KMS to encrypt and decrypt data. Each call adds latency (typically 10-50ms) and costs money.

=== "kms_metrics.py"
    ```python
    --8<-- "docs/examples/observability/kms_metrics.py"
    ```

### What's tracked

| Field | Type | Description |
|-------|------|-------------|
| `kms_duration_ms` | float | Total time spent on KMS calls |
| `kms_calls` | int | Number of KMS API calls |

### When metrics are collected

- `save()` - encrypts fields before writing to DynamoDB
- `get()` - decrypts fields after reading from DynamoDB
- `query()` / `scan()` - decrypts fields in each returned item

### Envelope encryption

pydynox uses envelope encryption. This means:

1. One `GenerateDataKey` call per encrypt operation
2. Local AES-256-GCM encryption (no KMS call per field)
3. One `Decrypt` call per decrypt operation

So even with multiple encrypted fields, you typically see 1 KMS call per save/get.

## S3 metrics

When you use `S3Attribute`, pydynox uploads and downloads files from S3. Track these operations to understand data transfer costs and latency.

=== "s3_metrics.py"
    ```python
    --8<-- "docs/examples/observability/s3_metrics.py"
    ```

### What's tracked

| Field | Type | Description |
|-------|------|-------------|
| `s3_duration_ms` | float | Total time spent on S3 calls |
| `s3_calls` | int | Number of S3 API calls |
| `s3_bytes_uploaded` | int | Total bytes uploaded to S3 |
| `s3_bytes_downloaded` | int | Total bytes downloaded from S3 |

### When metrics are collected

- `save()` - uploads `S3File` values to S3
- `delete()` - deletes associated S3 objects
- `async_save()` / `async_delete()` - async versions

### Multipart uploads

For files larger than 5MB, S3 uses multipart upload. The `s3_calls` field counts:

- Each part upload (one per 5MB chunk)
- The `CreateMultipartUpload` call
- The `CompleteMultipartUpload` call

A 15MB file would show ~5 S3 calls (create + 3 parts + complete).

## Combined metrics

All metrics are available through `get_total_metrics()`:

```python
metrics = MyModel.get_total_metrics()

# DynamoDB metrics
print(f"DynamoDB duration: {metrics.total_duration_ms}ms")
print(f"RCU: {metrics.total_rcu}, WCU: {metrics.total_wcu}")

# KMS metrics
print(f"KMS duration: {metrics.kms_duration_ms}ms")
print(f"KMS calls: {metrics.kms_calls}")

# S3 metrics
print(f"S3 duration: {metrics.s3_duration_ms}ms")
print(f"S3 calls: {metrics.s3_calls}")
print(f"S3 uploaded: {metrics.s3_bytes_uploaded} bytes")
print(f"S3 downloaded: {metrics.s3_bytes_downloaded} bytes")
```

## Reset metrics

In long-running processes, reset metrics at the start of each request:

```python
# At request start
MyModel.reset_metrics()

# ... do work ...

# At request end
metrics = MyModel.get_total_metrics()
log_metrics(metrics)
```

## Use cases

### Cost analysis

Track KMS and S3 costs per operation:

```python
metrics = User.get_total_metrics()

# KMS costs ~$0.03 per 10,000 requests
kms_cost = metrics.kms_calls * 0.000003

# S3 PUT costs ~$0.005 per 1,000 requests
s3_put_cost = metrics.s3_calls * 0.000005

# S3 data transfer ~$0.09 per GB
s3_transfer_cost = (metrics.s3_bytes_uploaded + metrics.s3_bytes_downloaded) / 1e9 * 0.09
```

### Performance debugging

Find where time is spent:

```python
metrics = Document.get_total_metrics()

total = metrics.total_duration_ms + metrics.kms_duration_ms + metrics.s3_duration_ms

print(f"DynamoDB: {metrics.total_duration_ms / total * 100:.1f}%")
print(f"KMS: {metrics.kms_duration_ms / total * 100:.1f}%")
print(f"S3: {metrics.s3_duration_ms / total * 100:.1f}%")
```

### Lambda optimization

In Lambda, every millisecond counts. Track all services:

```python
def handler(event, context):
    Document.reset_metrics()
    
    # ... process request ...
    
    metrics = Document.get_total_metrics()
    
    # Log for analysis
    logger.info({
        "dynamodb_ms": metrics.total_duration_ms,
        "kms_ms": metrics.kms_duration_ms,
        "s3_ms": metrics.s3_duration_ms,
        "s3_bytes": metrics.s3_bytes_uploaded + metrics.s3_bytes_downloaded,
    })
```

## Next steps

- [Encryption](encryption.md) - Field-level encryption with KMS
- [S3 attribute](s3-attribute.md) - Store large objects in S3
- [Observability](observability.md) - DynamoDB metrics and logging
