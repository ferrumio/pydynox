"""Basic S3 upload example."""

import asyncio

from pydynox import Model, ModelConfig
from pydynox.attributes import S3Attribute, S3File, StringAttribute


# Define model with S3Attribute
class Document(Model):
    model_config = ModelConfig(table="documents")

    pk = StringAttribute(partition_key=True)
    name = StringAttribute()
    content = S3Attribute(bucket="my-bucket", prefix="docs/")


async def main():
    # Upload from bytes
    doc = Document(pk="DOC#S3", name="report.pdf")
    doc.content = S3File(b"PDF content here", name="report.pdf", content_type="application/pdf")
    await doc.save()

    print(f"Uploaded to: s3://{doc.content.bucket}/{doc.content.key}")
    print(f"Size: {doc.content.size} bytes")
    print(f"ETag: {doc.content.etag}")


asyncio.run(main())
