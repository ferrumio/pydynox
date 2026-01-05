"""Upload with custom metadata."""

from pydynox import Model, ModelConfig, DynamoDBClient, set_default_client
from pydynox.attributes import StringAttribute, S3Attribute, S3File

# Setup client
client = DynamoDBClient(region="us-east-1")
set_default_client(client)


class Document(Model):
    model_config = ModelConfig(table="documents")

    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    name = StringAttribute()
    content = S3Attribute(bucket="my-bucket")


# Upload with metadata
doc = Document(pk="DOC#3", sk="v1", name="contract.pdf")
doc.content = S3File(
    b"Contract content...",
    name="contract.pdf",
    content_type="application/pdf",
    metadata={
        "author": "John Doe",
        "department": "Legal",
        "version": "2.0",
    },
)
doc.save()

# Access metadata
print(f"Author: {doc.content.metadata.get('author')}")
print(f"Version: {doc.content.metadata.get('version')}")
