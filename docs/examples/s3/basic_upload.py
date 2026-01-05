"""Basic S3 upload example."""

from pydynox import Model, ModelConfig, DynamoDBClient, set_default_client
from pydynox.attributes import StringAttribute, S3Attribute, S3File

# Setup client
client = DynamoDBClient(region="us-east-1")
set_default_client(client)


# Define model with S3Attribute
class Document(Model):
    model_config = ModelConfig(table="documents")

    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    name = StringAttribute()
    content = S3Attribute(bucket="my-bucket", prefix="docs/")


# Upload from bytes
doc = Document(pk="DOC#1", sk="v1", name="report.pdf")
doc.content = S3File(b"PDF content here", name="report.pdf", content_type="application/pdf")
doc.save()

print(f"Uploaded to: s3://{doc.content.bucket}/{doc.content.key}")
print(f"Size: {doc.content.size} bytes")
print(f"ETag: {doc.content.etag}")
