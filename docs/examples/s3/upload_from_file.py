"""Upload file from disk."""

from pathlib import Path

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


# Upload from file path
file_path = Path("/path/to/report.pdf")
doc = Document(pk="DOC#2", sk="v1", name=file_path.name)
doc.content = S3File(file_path)  # Name is taken from file
doc.save()

print(f"Uploaded: {doc.content.key}")
