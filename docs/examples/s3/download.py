"""Sync S3 download operations (with sync_ prefix)."""

from pydynox import Model, ModelConfig
from pydynox.attributes import S3Attribute, S3File, StringAttribute


class Document(Model):
    model_config = ModelConfig(table="documents")

    pk = StringAttribute(hash_key=True)
    name = StringAttribute()
    content = S3Attribute(bucket="my-bucket")


# First create a document with S3 content
doc = Document(pk="DOC#DOWNLOAD", name="report.pdf")
doc.content = S3File(b"PDF content here", name="report.pdf", content_type="application/pdf")
doc.save()  # Model.save() is sync

# Get document (sync)
doc = Document.get(pk="DOC#DOWNLOAD")

if doc and doc.content:
    # Download to memory (sync, with prefix)
    data = doc.content.sync_get_bytes()
    print(f"Downloaded {len(data)} bytes")

    # Stream to file (sync, with prefix)
    doc.content.sync_save_to("/tmp/downloaded.pdf")
    print("Saved to /tmp/downloaded.pdf")

    # Get presigned URL (sync, with prefix)
    url = doc.content.sync_presigned_url(expires=3600)  # 1 hour
    print(f"Presigned URL: {url}")
