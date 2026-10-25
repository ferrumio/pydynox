"""Static checks for S3 descriptor reads, writes, and narrowing."""

from __future__ import annotations

from typing import assert_type

from pydynox import Model, ModelConfig
from pydynox.attributes import S3Attribute, S3File, S3Value, StringAttribute


class Document(Model):
    model_config = ModelConfig(table="documents")
    pk = StringAttribute(partition_key=True)
    content = S3Attribute(bucket="my-bucket")


assert_type(Document.content, S3Attribute)


def check_reads(doc: Document) -> None:
    value = doc.content
    assert_type(value, S3File | S3Value | None)
    if isinstance(value, S3File):
        assert_type(value.data, bytes)
    elif isinstance(value, S3Value):
        assert_type(value.key, str)
    else:
        assert_type(value, None)


def check_writes(doc: Document, uploaded: S3Value) -> None:
    doc.content = S3File(b"hello", name="hello.txt")
    doc.content = uploaded
    doc.content = None


async def check_after_save(doc: Document) -> None:
    doc.content = S3File(b"hello", name="hello.txt")
    await doc.save()
    uploaded = doc.content
    assert isinstance(uploaded, S3Value)
    assert_type(uploaded.key, str)


def check_after_sync_save(doc: Document) -> None:
    doc.content = S3File(b"hello", name="hello.txt")
    doc.sync_save()
    uploaded = doc.content
    assert isinstance(uploaded, S3Value)
    assert_type(uploaded.key, str)
