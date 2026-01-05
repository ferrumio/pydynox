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

## Basic usage

=== "basic_upload.py"
    ```python
    --8<-- "docs/examples/s3/basic_upload.py"
    ```

## Uploading files

### From bytes

Use `S3File` to wrap your data. The `name` parameter is required when uploading bytes.

```python
doc.content = S3File(b"file content here", name="report.pdf")
doc.save()
```

### From file path

Pass a `Path` object. The filename is used automatically.

```python
from pathlib import Path

doc.content = S3File(Path("/path/to/report.pdf"))
doc.save()
```

### With content type

Set the MIME type for proper browser handling.

```python
doc.content = S3File(
    b"...",
    name="report.pdf",
    content_type="application/pdf"
)
doc.save()
```

### With custom metadata

Add your own key-value pairs. Stored in S3 as user metadata.

```python
doc.content = S3File(
    b"...",
    name="report.pdf",
    metadata={"author": "John", "version": "1.0"}
)
doc.save()
```

## Downloading files

After loading a model, `content` is an `S3Value` with methods to download.

### To memory

Downloads the entire file to memory. Be careful with large files.

```python
doc = Document.get(pk="DOC#1")
data = doc.content.get_bytes()
```

### To file (streaming)

Streams directly to disk. Memory efficient for large files.

```python
doc = Document.get(pk="DOC#1")
doc.content.save_to("/path/to/output.pdf")
```

### Presigned URL

Generate a temporary URL for sharing. The URL expires after the specified seconds.

```python
doc = Document.get(pk="DOC#1")
url = doc.content.presigned_url(expires=3600)  # 1 hour
print(url)  # https://my-bucket.s3.amazonaws.com/docs/DOC/1/report.pdf?...
```

Use presigned URLs when:

- Sharing files with users who don't have AWS credentials
- Serving files from a web application
- Avoiding data transfer through your server

## Accessing metadata

Metadata is always available without downloading the file.

```python
doc = Document.get(pk="DOC#1")

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
doc = Document.get(pk="DOC#1")
doc.delete()  # Deletes from DynamoDB AND S3
```

If you only want to remove the file reference without deleting from S3, set the attribute to `None` and save:

```python
doc.content = None
doc.save()  # Updates DynamoDB, S3 file remains
```

## Async operations

All operations have async versions.

```python
# Upload
doc.content = S3File(b"...", name="file.txt")
await doc.async_save()

# Download
doc = await Document.async_get(pk="DOC#1")
data = await doc.content.async_get_bytes()
await doc.content.async_save_to("/path/to/file.txt")
url = await doc.content.async_presigned_url(3600)

# Delete
await doc.async_delete()
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
{prefix}{hash_key}/{range_key}/{filename}
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
content = S3Attribute(bucket="my-bucket", null=False)
```

## Error handling

```python
from pydynox.exceptions import S3AttributeError

try:
    doc.content = S3File(b"...", name="file.txt")
    doc.save()
except S3AttributeError as e:
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
from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute, S3Attribute, DatetimeAttribute, AutoGenerate
from pydynox._internal._s3 import S3File

class Document(Model):
    model_config = ModelConfig(table="documents", client=client)
    
    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True, default="v1")
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
doc.save()

# List documents (fast, no S3 calls)
for doc in Document.query(hash_key="DOC#invoice-2024-001"):
    print(f"{doc.name}: {doc.content.size} bytes")

# Generate download link
url = doc.content.presigned_url(expires=3600)
print(f"Download: {url}")
```
