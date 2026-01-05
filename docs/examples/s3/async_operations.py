"""Async S3 operations."""

import asyncio

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


async def main():
    # Async upload
    doc = Document(pk="DOC#async", sk="v1", name="async.txt")
    doc.content = S3File(b"Async content", name="async.txt")
    await doc.async_save()
    print(f"Uploaded: {doc.content.key}")

    # Async get
    loaded = await Document.async_get(pk="DOC#async", sk="v1")
    if loaded and loaded.content:
        # Async download
        data = await loaded.content.async_get_bytes()
        print(f"Downloaded: {len(data)} bytes")

        # Async save to file
        await loaded.content.async_save_to("/tmp/async_download.txt")

        # Async presigned URL
        url = await loaded.content.async_presigned_url(3600)
        print(f"URL: {url}")

    # Async delete
    await doc.async_delete()
    print("Deleted")


if __name__ == "__main__":
    asyncio.run(main())
