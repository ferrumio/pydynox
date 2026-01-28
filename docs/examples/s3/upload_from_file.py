"""Upload file from disk."""

import asyncio
import tempfile
from pathlib import Path

from pydynox import Model, ModelConfig
from pydynox.attributes import S3Attribute, S3File, StringAttribute


class Document(Model):
    model_config = ModelConfig(table="documents")

    pk = StringAttribute(hash_key=True)
    name = StringAttribute()
    content = S3Attribute(bucket="my-bucket")


async def main():
    # Create a temp file for demo
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("This is a test file content")
        file_path = Path(f.name)

    # Upload from file path
    doc = Document(pk="DOC#FILE", name=file_path.name)
    doc.content = S3File(file_path)  # Name is taken from file
    await doc.save()

    print(f"Uploaded: {doc.content.key}")

    # Cleanup
    file_path.unlink()


asyncio.run(main())
