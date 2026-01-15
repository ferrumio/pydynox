"""Integration tests for S3 metrics in Model observability."""

import uuid

import pytest
from pydynox import DynamoDBClient, Model, ModelConfig, set_default_client
from pydynox._internal._s3 import S3File
from pydynox.attributes import S3Attribute, StringAttribute


@pytest.fixture
def s3_model(dynamo: DynamoDBClient, s3_bucket: str):
    """Model with S3Attribute for testing metrics."""
    set_default_client(dynamo)

    class Document(Model):
        model_config = ModelConfig(table="test_table")

        pk = StringAttribute(hash_key=True)
        sk = StringAttribute(range_key=True)
        name = StringAttribute()
        content = S3Attribute(bucket=s3_bucket, prefix="docs/")

    # Reset metrics before each test
    Document.reset_metrics()
    return Document


def test_s3_metrics_on_save(s3_model):
    """S3 metrics are recorded when saving with S3File."""
    doc_id = str(uuid.uuid4())

    # GIVEN a model with S3File
    doc = s3_model(pk=f"DOC#{doc_id}", sk="v1", name="test.txt")
    doc.content = S3File(b"Hello, S3 metrics!", name="test.txt")

    # WHEN we save
    doc.save()

    # THEN S3 metrics should be recorded
    metrics = s3_model.get_total_metrics()
    assert metrics.s3_calls >= 1
    assert metrics.s3_duration_ms > 0
    assert metrics.s3_bytes_uploaded == len(b"Hello, S3 metrics!")
    assert metrics.s3_bytes_downloaded == 0


def test_s3_metrics_on_delete(s3_model):
    """S3 metrics are recorded when deleting model with S3 file."""
    doc_id = str(uuid.uuid4())

    # GIVEN a saved model with S3 content
    doc = s3_model(pk=f"DOC#{doc_id}", sk="v1", name="to_delete.txt")
    doc.content = S3File(b"Content to delete", name="to_delete.txt")
    doc.save()

    # Reset metrics to isolate delete metrics
    s3_model.reset_metrics()

    # WHEN we delete
    doc.delete()

    # THEN S3 delete metrics should be recorded
    metrics = s3_model.get_total_metrics()
    assert metrics.s3_calls >= 1
    assert metrics.s3_duration_ms > 0
    # Delete doesn't transfer bytes
    assert metrics.s3_bytes_uploaded == 0
    assert metrics.s3_bytes_downloaded == 0


def test_s3_metrics_accumulate(s3_model):
    """S3 metrics accumulate across multiple operations."""
    # GIVEN multiple saves with S3 content
    for i in range(3):
        doc_id = str(uuid.uuid4())
        doc = s3_model(pk=f"DOC#{doc_id}", sk="v1", name=f"file{i}.txt")
        doc.content = S3File(f"Content {i}".encode(), name=f"file{i}.txt")
        doc.save()

    # THEN metrics should accumulate
    metrics = s3_model.get_total_metrics()
    assert metrics.s3_calls >= 3
    assert metrics.s3_bytes_uploaded > 0


def test_s3_metrics_zero_without_s3_operations(dynamo: DynamoDBClient):
    """S3 metrics are zero when no S3 operations happen."""
    set_default_client(dynamo)

    class SimpleModel(Model):
        model_config = ModelConfig(table="test_table")

        pk = StringAttribute(hash_key=True)
        sk = StringAttribute(range_key=True)
        name = StringAttribute()

    SimpleModel.reset_metrics()

    # WHEN we save a model without S3
    doc_id = str(uuid.uuid4())
    item = SimpleModel(pk=f"SIMPLE#{doc_id}", sk="v1", name="No S3")
    item.save()

    # THEN S3 metrics should be zero
    metrics = SimpleModel.get_total_metrics()
    assert metrics.s3_calls == 0
    assert metrics.s3_duration_ms == 0.0
    assert metrics.s3_bytes_uploaded == 0
    assert metrics.s3_bytes_downloaded == 0


def test_s3_metrics_reset(s3_model):
    """S3 metrics are cleared on reset."""
    doc_id = str(uuid.uuid4())

    # GIVEN a model with S3 metrics
    doc = s3_model(pk=f"DOC#{doc_id}", sk="v1", name="reset.txt")
    doc.content = S3File(b"Content", name="reset.txt")
    doc.save()

    # Verify metrics exist
    metrics = s3_model.get_total_metrics()
    assert metrics.s3_calls > 0

    # WHEN we reset
    s3_model.reset_metrics()

    # THEN S3 metrics should be zero
    metrics = s3_model.get_total_metrics()
    assert metrics.s3_calls == 0
    assert metrics.s3_duration_ms == 0.0
    assert metrics.s3_bytes_uploaded == 0
    assert metrics.s3_bytes_downloaded == 0


@pytest.mark.asyncio
async def test_s3_metrics_async_save(s3_model):
    """S3 metrics are recorded on async save."""
    doc_id = str(uuid.uuid4())

    # GIVEN a model with S3File
    doc = s3_model(pk=f"DOC#{doc_id}", sk="v1", name="async.txt")
    doc.content = S3File(b"Async S3 content", name="async.txt")

    # WHEN we async save
    await doc.async_save()

    # THEN S3 metrics should be recorded
    metrics = s3_model.get_total_metrics()
    assert metrics.s3_calls >= 1
    assert metrics.s3_duration_ms > 0
    assert metrics.s3_bytes_uploaded == len(b"Async S3 content")


@pytest.mark.asyncio
async def test_s3_metrics_async_delete(s3_model):
    """S3 metrics are recorded on async delete."""
    doc_id = str(uuid.uuid4())

    # GIVEN a saved model with S3 content
    doc = s3_model(pk=f"DOC#{doc_id}", sk="v1", name="async_delete.txt")
    doc.content = S3File(b"Async delete content", name="async_delete.txt")
    await doc.async_save()

    # Reset metrics
    s3_model.reset_metrics()

    # WHEN we async delete
    await doc.async_delete()

    # THEN S3 delete metrics should be recorded
    metrics = s3_model.get_total_metrics()
    assert metrics.s3_calls >= 1
    assert metrics.s3_duration_ms > 0
