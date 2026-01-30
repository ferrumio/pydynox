# S3 attribute

Store large files in S3 with metadata in DynamoDB.

DynamoDB has a 400KB item limit. For larger files, use `S3Attribute` to store the file in S3 and keep only the metadata in DynamoDB. This is a common pattern that pydynox handles automatically.

## How it works

When you save a model with an `S3Attribute`:

1. The file is uploaded to S3
2. Metadata (bucket, key, size, etag, content_type) is stored in DynamoDB
3. The file content never touches DynamoDB

When you load a model:

1. Only metadata is read from DynamoDB (fast, no S3 call)
2. You can access file properties like `size` and `content_type` immediately
3. The actual file is downloaded only when you call `get_bytes()` or `save_to()`

When you delete a model:

1. The item is deleted from DynamoDB
2. The file is deleted from S3

!!! warning "Partial failure and orphan objects"
    The write order is S3 first, then DynamoDB. If S3 upload succeeds but DynamoDB write fails, an orphan object is left in S3. This is a known limitation.

    Orphans are harmless (just storage cost). To clean them up, set up an [S3 lifecycle rule](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html) to delete objects older than a certain age.

## S3Value methods

S3Value methods follow the async-first pattern. Async is the default (no prefix), sync has `sync_` prefix.

| Operation | Async (default) | Sync |
|-----------|-----------------|------|
| Download to memory | `await value.get_bytes()` | `value.sync_get_bytes()` |
| Save to file | `await value.save_to(path)` | `value.sync_save_to(path)` |
| Presigned URL | `await value.presigned_url(expires)` | `value.sync_presigned_url(expires)` |

## Basic usage

```python
from pydynox import Model, ModelConfig
from pydynox.attributes import S3Attribute, S3File, StringAttribute

class Document(Model):
    model_config = ModelConfig(table="documents")
    pk = StringAttribute(partition_key=True)
    content = S3Attribute(bucket="my-bucket", prefix="docs/")

# Upload
doc = Document(pk="DOC#1")
doc.content = S3File(b"file content", name="report.pdf")
await doc.save()

# Download
doc = await Document.get(pk="DOC#1")
data = await doc.content.get_bytes()
await doc.content.save_to("/tmp/report.pdf")
url = await doc.content.presigned_url(3600)

# Sync alternative (use sync_ prefix)
data = doc.content.sync_get_bytes()
doc.content.sync_save_to("/tmp/report.pdf")
url = doc.content.sync_presigned_url(3600)
```

## Uploading files

### From bytes

Use `S3File` to wrap your data. The `name` parameter is required.

```python
doc.content = S3File(b"file content here", name="report.pdf")
await doc.save()
```

### From file path

Pass a `Path` object. The filename is used automatically.

```python
from pathlib import Path

doc.content = S3File(Path("/path/to/report.pdf"))
await doc.save()
```

### With content type

Set the MIME type for proper browser handling.

```python
doc.content = S3File(
    b"...",
    name="report.pdf",
    content_type="application/pdf"
)
```

### With custom metadata

Add your own key-value pairs. Stored in S3 as user metadata.

```python
doc.content = S3File(
    b"...",
    name="report.pdf",
    metadata={"author": "John", "version": "1.0"}
)
```

## Downloading files

After loading a model, `content` is an `S3Value`. Use async methods by default.

```python
doc = await Document.get(pk="DOC#1")

# Download to memory (careful with large files)
data = await doc.content.get_bytes()

# Stream to file (memory efficient)
await doc.content.save_to("/path/to/output.pdf")

# Generate presigned URL for sharing
url = await doc.content.presigned_url(expires=3600)
```

Use presigned URLs when:

- Sharing files with users who don't have AWS credentials
- Serving files from a web application
- Avoiding data transfer through your server

## Accessing metadata

Metadata is always available without downloading the file.

```python
doc = await Document.get(pk="DOC#1")

# These don't make S3 calls
print(doc.content.bucket)        # "my-bucket"
print(doc.content.key)           # "docs/DOC/1/report.pdf"
print(doc.content.size)          # 1048576 (bytes)
print(doc.content.etag)          # "d41d8cd98f00b204e9800998ecf8427e"
print(doc.content.content_type)  # "application/pdf"
print(doc.content.last_modified) # "2024-01-15T10:30:00Z"
print(doc.content.version_id)    # "abc123" (if versioning enabled)
print(doc.content.metadata)      # {"author": "John", "version": "1.0"}
```

## Deleting files

When you delete the model, the S3 file is also deleted.

```python
doc = await Document.get(pk="DOC#1")
await doc.delete()  # Deletes from DynamoDB AND S3
```

To remove the file reference without deleting from S3:

```python
doc.content = None
await doc.save()  # Updates DynamoDB, S3 file remains
```

## S3 region

By default, S3Attribute uses the same region as your DynamoDB client. To use a different region:

```python
content = S3Attribute(bucket="my-bucket", region="eu-west-1")
```

## Credentials

S3Attribute inherits all credentials and config from your DynamoDB client:

- Access key / secret key
- Session token
- IAM role
- Profile
- Endpoint URL (for LocalStack/MinIO)
- Timeouts and retries
- Proxy settings

No extra configuration needed.

## S3 key structure

Files are stored with this key pattern:

```
{prefix}{partition_key}/{sort_key}/{filename}
```

For example, with `prefix="docs/"`, `pk="DOC#1"`, `sk="v1"`, and filename `report.pdf`:

```
docs/DOC/1/v1/report.pdf
```

The `#` character is replaced with `/` for cleaner S3 paths.

## What gets stored in DynamoDB

Only metadata is stored. The actual file is in S3.

```json
{
  "pk": {"S": "DOC#1"},
  "name": {"S": "report.pdf"},
  "content": {
    "M": {
      "bucket": {"S": "my-bucket"},
      "key": {"S": "docs/DOC/1/report.pdf"},
      "size": {"N": "1048576"},
      "etag": {"S": "d41d8cd98f00b204e9800998ecf8427e"},
      "content_type": {"S": "application/pdf"}
    }
  }
}
```

This keeps your DynamoDB items small and fast to read.

## Multipart upload

Files larger than 10MB are automatically uploaded using multipart upload. This is handled by the Rust core for speed. You don't need to do anything different.

## Null values

S3Attribute can be null by default. If you want to require a file:

```python
content = S3Attribute(bucket="my-bucket", required=True)
```

## Error handling

```python
from pydynox.exceptions import S3AttributeException

try:
    doc.content = S3File(b"...", name="file.txt")
    await doc.save()
except S3AttributeException as e:
    print(f"S3 error: {e}")
```

Common errors:

- Bucket doesn't exist
- Access denied (check IAM permissions)
- Network timeout

## IAM permissions

Your IAM role needs these S3 permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::my-bucket/*"
    }
  ]
}
```

For presigned URLs, no extra permissions are needed on the client side. The URL contains temporary credentials.

## When to use S3Attribute

Use S3Attribute when:

- Files are larger than a few KB
- You need to serve files directly to users (presigned URLs)
- You want to keep DynamoDB costs low (storage is cheaper in S3)
- Files might exceed the 400KB DynamoDB limit

Don't use S3Attribute when:

- Data is small (< 1KB) - just use `BinaryAttribute`
- You need to query by file content
- You need atomic updates of file + metadata


## Example: document management

```python
from pathlib import Path
from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute, S3Attribute, DatetimeAttribute, AutoGenerate
from pydynox._internal._s3 import S3File

class Document(Model):
    model_config = ModelConfig(table="documents")
    
    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True, default="v1")
    name = StringAttribute()
    uploaded_at = DatetimeAttribute(default=AutoGenerate.utc_now())
    content = S3Attribute(bucket="company-docs", prefix="documents/")

# Upload a new document
doc = Document(pk="DOC#invoice-2024-001", name="Invoice January 2024")
doc.content = S3File(
    Path("/tmp/invoice.pdf"),
    content_type="application/pdf",
    metadata={"department": "finance"}
)
await doc.save()

# List documents (fast, no S3 calls)
async for doc in Document.query(partition_key="DOC#invoice-2024-001"):
    print(f"{doc.name}: {doc.content.size} bytes")

# Generate download link
url = await doc.content.presigned_url(expires=3600)
print(f"Download: {url}")
```
