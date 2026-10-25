"""Upload with custom metadata."""

import asyncio

from pydynox import Model, ModelConfig
from pydynox.attributes import S3Attribute, S3File, S3Value, StringAttribute


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
    uploaded = doc.content
    assert isinstance(uploaded, S3Value)
    assert uploaded.metadata is not None
    print(f"Author: {uploaded.metadata.get('author')}")
    print(f"Version: {uploaded.metadata.get('version')}")


asyncio.run(main())
