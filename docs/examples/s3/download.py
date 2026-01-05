"""Download S3 content."""

from pydynox import DynamoDBClient, Model, ModelConfig, set_default_client
from pydynox.attributes import S3Attribute, StringAttribute

# Setup client
client = DynamoDBClient(region="us-east-1")
set_default_client(client)


class Document(Model):
    model_config = ModelConfig(table="documents")

    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    name = StringAttribute()
    content = S3Attribute(bucket="my-bucket")


# Get document
doc = Document.get(pk="DOC#1", sk="v1")

if doc and doc.content:
    # Download to memory (careful with large files)
    data = doc.content.get_bytes()
    print(f"Downloaded {len(data)} bytes")

    # Stream to file (memory efficient for large files)
    doc.content.save_to("/tmp/downloaded.pdf")
    print("Saved to /tmp/downloaded.pdf")

    # Get presigned URL for sharing
    url = doc.content.presigned_url(expires=3600)  # 1 hour
    print(f"Presigned URL: {url}")
