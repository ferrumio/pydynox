"""Upload with custom metadata."""

import asyncio

from pydynox import Model, ModelConfig
from pydynox.attributes import S3Attribute, S3File, StringAttribute


class Document(Model):
    model_config = ModelConfig(table="documents")

    pk = StringAttribute(partition_key=True)
    name = StringAttribute()
    content = S3Attribute(bucket="my-bucket")


async def main():
    # Upload with metadata
    doc = Document(pk="DOC#META", name="contract.pdf")
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
    await doc.save()

    # Access metadata
    print(f"Author: {doc.content.metadata.get('author')}")
    print(f"Version: {doc.content.metadata.get('version')}")


asyncio.run(main())
