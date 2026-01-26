"""Async S3 operations (S3Value methods are async-first)."""

import asyncio

from pydynox import DynamoDBClient, Model, ModelConfig, set_default_client
from pydynox.attributes import S3Attribute, S3File, StringAttribute

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
    # Upload (Model uses async_save)
    doc = Document(pk="DOC#async", sk="v1", name="async.txt")
    doc.content = S3File(b"Async content", name="async.txt")
    await doc.async_save()
    print(f"Uploaded: {doc.content.key}")

    # Get (Model uses async_get)
    loaded = await Document.async_get(pk="DOC#async", sk="v1")
    if loaded and loaded.content:
        # S3Value methods are async-first (no prefix = async)
        data = await loaded.content.get_bytes()
        print(f"Downloaded: {len(data)} bytes")

        await loaded.content.save_to("/tmp/async_download.txt")

        url = await loaded.content.presigned_url(3600)
        print(f"URL: {url}")

    # Delete (Model uses async_delete)
    await doc.async_delete()
    print("Deleted")


if __name__ == "__main__":
    asyncio.run(main())
