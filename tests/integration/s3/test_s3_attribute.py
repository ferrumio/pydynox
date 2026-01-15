"""Integration tests for S3Attribute with LocalStack."""

import uuid

import pytest
from pydynox import Model, ModelConfig, set_default_client
from pydynox._internal._s3 import S3File, S3Value
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


def test_save_with_s3file(document_model):
    """Model.save() uploads S3File to S3."""
    doc_id = str(uuid.uuid4())

    # GIVEN a document with S3File content
    doc = document_model(
        pk=f"DOC#{doc_id}",
        sk="v1",
        name="report.pdf",
    )
    doc.content = S3File(b"PDF content here", name="report.pdf", content_type="application/pdf")

    # WHEN we save it
    doc.save()

    # THEN content becomes S3Value with metadata
    assert isinstance(doc.content, S3Value)
    assert doc.content.size == 16
    assert doc.content.content_type == "application/pdf"


def test_get_returns_s3value(document_model):
    """Model.get() returns S3Value for S3Attribute."""
    doc_id = str(uuid.uuid4())

    # GIVEN a saved document with S3 content
    doc = document_model(
        pk=f"DOC#{doc_id}",
        sk="v1",
        name="test.txt",
    )
    doc.content = S3File(b"Hello World", name="test.txt")
    doc.save()

    # WHEN we get the document
    loaded = document_model.get(pk=f"DOC#{doc_id}", sk="v1")

    # THEN content is S3Value
    assert loaded is not None
    assert isinstance(loaded.content, S3Value)
    assert loaded.content.size == 11


def test_s3value_get_bytes(document_model):
    """S3Value.get_bytes() downloads file content."""
    doc_id = str(uuid.uuid4())
    content = b"File content for download test"

    doc = document_model(
        pk=f"DOC#{doc_id}",
        sk="v1",
        name="download.txt",
    )
    doc.content = S3File(content, name="download.txt")
    doc.save()

    # Get and download
    loaded = document_model.get(pk=f"DOC#{doc_id}", sk="v1")

    # Set s3_ops on the loaded value
    loaded._attributes["content"]._get_s3_ops(loaded._get_client())
    loaded.content._s3_ops = loaded._attributes["content"]._s3_ops

    downloaded = loaded.content.get_bytes()
    assert downloaded == content


def test_s3value_presigned_url(document_model):
    """S3Value.presigned_url() generates URL."""
    doc_id = str(uuid.uuid4())

    doc = document_model(
        pk=f"DOC#{doc_id}",
        sk="v1",
        name="presigned.txt",
    )
    doc.content = S3File(b"data", name="presigned.txt")
    doc.save()

    loaded = document_model.get(pk=f"DOC#{doc_id}", sk="v1")

    # Set s3_ops
    loaded._attributes["content"]._get_s3_ops(loaded._get_client())
    loaded.content._s3_ops = loaded._attributes["content"]._s3_ops

    url = loaded.content.presigned_url(3600)

    assert url.startswith("http")


def test_s3value_save_to_file(document_model, tmp_path):
    """S3Value.save_to() streams to file."""
    doc_id = str(uuid.uuid4())
    content = b"Large file content " * 100

    doc = document_model(
        pk=f"DOC#{doc_id}",
        sk="v1",
        name="large.bin",
    )
    doc.content = S3File(content, name="large.bin")
    doc.save()

    loaded = document_model.get(pk=f"DOC#{doc_id}", sk="v1")

    # Set s3_ops
    loaded._attributes["content"]._get_s3_ops(loaded._get_client())
    loaded.content._s3_ops = loaded._attributes["content"]._s3_ops

    output_path = tmp_path / "downloaded.bin"
    loaded.content.save_to(output_path)

    assert output_path.read_bytes() == content


def test_delete_removes_s3_file(document_model):
    """Model.delete() removes file from S3."""
    doc_id = str(uuid.uuid4())

    doc = document_model(
        pk=f"DOC#{doc_id}",
        sk="v1",
        name="to_delete.txt",
    )
    doc.content = S3File(b"will be deleted", name="to_delete.txt")
    doc.save()

    doc.delete()

    # Verify deleted from DynamoDB
    loaded = document_model.get(pk=f"DOC#{doc_id}", sk="v1")
    assert loaded is None


def test_s3file_with_metadata(document_model):
    """S3File metadata is stored in S3."""
    doc_id = str(uuid.uuid4())

    doc = document_model(
        pk=f"DOC#{doc_id}",
        sk="v1",
        name="with_meta.txt",
    )
    doc.content = S3File(
        b"data with metadata",
        name="with_meta.txt",
        metadata={"author": "test", "version": "1.0"},
    )
    doc.save()

    assert doc.content.metadata == {"author": "test", "version": "1.0"}


def test_null_s3attribute(document_model):
    """S3Attribute can be null."""
    doc_id = str(uuid.uuid4())

    doc = document_model(
        pk=f"DOC#{doc_id}",
        sk="v1",
        name="no_content.txt",
    )
    # content is None by default

    doc.save()

    loaded = document_model.get(pk=f"DOC#{doc_id}", sk="v1")
    assert loaded.content is None


def test_update_s3file(document_model):
    """S3File can be updated."""
    doc_id = str(uuid.uuid4())

    # Create initial
    doc = document_model(
        pk=f"DOC#{doc_id}",
        sk="v1",
        name="update.txt",
    )
    doc.content = S3File(b"version 1", name="update.txt")
    doc.save()

    # Update
    doc.content = S3File(b"version 2", name="update.txt")
    doc.save()

    # Verify
    loaded = document_model.get(pk=f"DOC#{doc_id}", sk="v1")

    loaded._attributes["content"]._get_s3_ops(loaded._get_client())
    loaded.content._s3_ops = loaded._attributes["content"]._s3_ops

    assert loaded.content.get_bytes() == b"version 2"
