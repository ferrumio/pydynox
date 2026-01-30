"""Async S3 operations (S3Value methods are async-first)."""

import asyncio

from pydynox import DynamoDBClient, Model, ModelConfig, set_default_client
from pydynox.attributes import S3Attribute, S3File, StringAttribute

# Setup client
client = DynamoDBClient(region="us-east-1")
set_default_client(client)


class Document(Model):
    model_config = ModelConfig(table="documents")

    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
    name = StringAttribute()
    content = S3Attribute(bucket="my-bucket")


async def main():
    # Upload
    doc = Document(pk="DOC#async", sk="v1", name="async.txt")
    doc.content = S3File(b"Async content", name="async.txt")
    await doc.save()
    print(f"Uploaded: {doc.content.key}")

    # Get
    loaded = await Document.get(pk="DOC#async", sk="v1")
    if loaded and loaded.content:
        # S3Value methods are async-first (no prefix = async)
        data = await loaded.content.get_bytes()
        print(f"Downloaded: {len(data)} bytes")

        await loaded.content.save_to("/tmp/async_download.txt")

        url = await loaded.content.presigned_url(3600)
        print(f"URL: {url}")

    # Delete
    await doc.delete()
    print("Deleted")


if __name__ == "__main__":
    asyncio.run(main())
