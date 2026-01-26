"""Async integration tests for S3Attribute.

Minimal tests to validate async API works. Full coverage is in test_s3_attribute.py.
"""

import uuid

import pytest
from pydynox import Model, ModelConfig, set_default_client
from pydynox._internal._s3 import S3File
from pydynox.attributes import S3Attribute, StringAttribute


@pytest.fixture
def document_model(dynamo, s3_bucket, localstack_endpoint):
    """Create a Document model with S3Attribute."""
    set_default_client(dynamo)

    table_name = "test_table"

    class Document(Model):
        model_config = ModelConfig(table=table_name)

        pk = StringAttribute(hash_key=True)
        sk = StringAttribute(range_key=True)
        name = StringAttribute()
        content = S3Attribute(bucket=s3_bucket)

    return Document


@pytest.mark.asyncio
async def test_async_get_bytes(document_model):
    """Test async get_bytes() downloads file content."""
    doc_id = str(uuid.uuid4())
    content = b"Async download test content"

    doc = document_model(
        pk=f"DOC#{doc_id}",
        sk="v1",
        name="async_download.txt",
    )
    doc.content = S3File(content, name="async_download.txt")
    doc.save()

    loaded = document_model.get(pk=f"DOC#{doc_id}", sk="v1")

    # Set s3_ops
    loaded._attributes["content"]._get_s3_ops(loaded._get_client())
    loaded.content._s3_ops = loaded._attributes["content"]._s3_ops

    downloaded = await loaded.content.get_bytes()
    assert downloaded == content


@pytest.mark.asyncio
async def test_async_presigned_url(document_model):
    """Test async presigned_url() generates URL."""
    doc_id = str(uuid.uuid4())

    doc = document_model(
        pk=f"DOC#{doc_id}",
        sk="v1",
        name="async_presigned.txt",
    )
    doc.content = S3File(b"data", name="async_presigned.txt")
    doc.save()

    loaded = document_model.get(pk=f"DOC#{doc_id}", sk="v1")

    # Set s3_ops
    loaded._attributes["content"]._get_s3_ops(loaded._get_client())
    loaded.content._s3_ops = loaded._attributes["content"]._s3_ops

    url = await loaded.content.presigned_url(3600)
    assert url.startswith("http")


@pytest.mark.asyncio
async def test_async_save_to(document_model, tmp_path):
    """Test async save_to() streams to file."""
    doc_id = str(uuid.uuid4())
    content = b"Async save to file content"

    doc = document_model(
        pk=f"DOC#{doc_id}",
        sk="v1",
        name="async_save.bin",
    )
    doc.content = S3File(content, name="async_save.bin")
    doc.save()

    loaded = document_model.get(pk=f"DOC#{doc_id}", sk="v1")

    # Set s3_ops
    loaded._attributes["content"]._get_s3_ops(loaded._get_client())
    loaded.content._s3_ops = loaded._attributes["content"]._s3_ops

    output_path = tmp_path / "async_downloaded.bin"
    await loaded.content.save_to(output_path)

    assert output_path.read_bytes() == content
