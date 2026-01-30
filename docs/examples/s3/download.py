"""Sync S3 download operations (with sync_ prefix)."""

import asyncio

from pydynox import Model, ModelConfig
from pydynox.attributes import S3Attribute, S3File, StringAttribute


class Document(Model):
    model_config = ModelConfig(table="documents")

    pk = StringAttribute(partition_key=True)
    name = StringAttribute()
    content = S3Attribute(bucket="my-bucket")


async def main():
    # First create a document with S3 content
    doc = Document(pk="DOC#DOWNLOAD", name="report.pdf")
    doc.content = S3File(b"PDF content here", name="report.pdf", content_type="application/pdf")
    await doc.save()

    # Get document
    doc = await Document.get(pk="DOC#DOWNLOAD")

    if doc and doc.content:
        # Download to memory
        data = await doc.content.get_bytes()
        print(f"Downloaded {len(data)} bytes")

        # Stream to file
        await doc.content.save_to("/tmp/downloaded.pdf")
        print("Saved to /tmp/downloaded.pdf")

        # Get presigned URL
        url = await doc.content.presigned_url(expires=3600)  # 1 hour
        print(f"Presigned URL: {url}")


asyncio.run(main())
