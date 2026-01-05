"""Unit tests for S3Attribute."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pydynox._internal._s3 import S3File, S3Value
from pydynox.attributes.s3 import S3Attribute


def test_s3file_from_bytes():
    """S3File can be created from bytes."""
    data = b"hello world"
    f = S3File(data, name="test.txt")

    assert f.data == data
    assert f.name == "test.txt"
    assert f.size == 11
    assert f.content_type is None
    assert f.metadata is None


def test_s3file_from_bytes_with_content_type():
    """S3File accepts content_type."""
    f = S3File(b"data", name="doc.pdf", content_type="application/pdf")

    assert f.content_type == "application/pdf"


def test_s3file_from_bytes_with_metadata():
    """S3File accepts metadata."""
    f = S3File(b"data", name="doc.pdf", metadata={"env": "prod", "version": "1"})

    assert f.metadata == {"env": "prod", "version": "1"}


def test_s3file_from_bytes_requires_name():
    """S3File from bytes requires name."""
    with pytest.raises(ValueError, match="name is required"):
        S3File(b"data")


def test_s3file_from_path(tmp_path):
    """S3File can be created from Path."""
    file_path = tmp_path / "test.txt"
    file_path.write_bytes(b"file content")

    f = S3File(file_path)

    assert f.data == b"file content"
    assert f.name == "test.txt"
    assert f.size == 12


def test_s3file_from_path_with_custom_name(tmp_path):
    """S3File from Path can override name."""
    file_path = tmp_path / "original.txt"
    file_path.write_bytes(b"data")

    f = S3File(file_path, name="custom.txt")

    assert f.name == "custom.txt"


def test_s3value_properties():
    """S3Value exposes all properties."""
    mock_ops = MagicMock()
    v = S3Value(
        bucket="my-bucket",
        key="path/to/file.txt",
        size=1024,
        etag="abc123",
        content_type="text/plain",
        s3_ops=mock_ops,
        last_modified="2025-01-05T10:00:00Z",
        version_id="v1",
        metadata={"key": "value"},
    )

    assert v.bucket == "my-bucket"
    assert v.key == "path/to/file.txt"
    assert v.size == 1024
    assert v.etag == "abc123"
    assert v.content_type == "text/plain"
    assert v.last_modified == "2025-01-05T10:00:00Z"
    assert v.version_id == "v1"
    assert v.metadata == {"key": "value"}


def test_s3value_get_bytes():
    """S3Value.get_bytes() calls s3_ops.download_bytes."""
    mock_ops = MagicMock()
    mock_ops.download_bytes.return_value = b"downloaded data"

    v = S3Value(
        bucket="bucket",
        key="key",
        size=100,
        etag="etag",
        content_type=None,
        s3_ops=mock_ops,
    )

    result = v.get_bytes()

    assert result == b"downloaded data"
    mock_ops.download_bytes.assert_called_once_with("bucket", "key")


def test_s3value_save_to():
    """S3Value.save_to() calls s3_ops.save_to_file."""
    mock_ops = MagicMock()
    v = S3Value(
        bucket="bucket",
        key="key",
        size=100,
        etag="etag",
        content_type=None,
        s3_ops=mock_ops,
    )

    v.save_to("/tmp/output.txt")

    mock_ops.save_to_file.assert_called_once_with("bucket", "key", "/tmp/output.txt")


def test_s3value_save_to_path_object():
    """S3Value.save_to() accepts Path object."""
    mock_ops = MagicMock()
    v = S3Value(
        bucket="bucket",
        key="key",
        size=100,
        etag="etag",
        content_type=None,
        s3_ops=mock_ops,
    )

    v.save_to(Path("/tmp/output.txt"))

    mock_ops.save_to_file.assert_called_once_with("bucket", "key", "/tmp/output.txt")


def test_s3value_presigned_url():
    """S3Value.presigned_url() calls s3_ops.presigned_url."""
    mock_ops = MagicMock()
    mock_ops.presigned_url.return_value = "https://presigned.url"

    v = S3Value(
        bucket="bucket",
        key="key",
        size=100,
        etag="etag",
        content_type=None,
        s3_ops=mock_ops,
    )

    result = v.presigned_url(7200)

    assert result == "https://presigned.url"
    mock_ops.presigned_url.assert_called_once_with("bucket", "key", 7200)


def test_s3value_presigned_url_default_expiry():
    """S3Value.presigned_url() defaults to 3600 seconds."""
    mock_ops = MagicMock()
    v = S3Value(
        bucket="bucket",
        key="key",
        size=100,
        etag="etag",
        content_type=None,
        s3_ops=mock_ops,
    )

    v.presigned_url()

    mock_ops.presigned_url.assert_called_once_with("bucket", "key", 3600)


def test_s3value_repr():
    """S3Value has readable repr."""
    mock_ops = MagicMock()
    v = S3Value(
        bucket="my-bucket",
        key="path/file.txt",
        size=1024,
        etag="etag",
        content_type=None,
        s3_ops=mock_ops,
    )

    assert repr(v) == "S3Value(bucket='my-bucket', key='path/file.txt', size=1024)"


def test_s3attribute_init():
    """S3Attribute stores bucket and prefix."""
    attr = S3Attribute(bucket="my-bucket", prefix="docs/")

    assert attr.bucket == "my-bucket"
    assert attr.prefix == "docs/"


def test_s3attribute_prefix_normalized():
    """S3Attribute normalizes prefix to end with /."""
    attr = S3Attribute(bucket="bucket", prefix="path/to/files")

    assert attr.prefix == "path/to/files/"


def test_s3attribute_empty_prefix():
    """S3Attribute handles empty prefix."""
    attr = S3Attribute(bucket="bucket")

    assert attr.prefix == ""


def test_s3attribute_cannot_be_hash_key():
    """S3Attribute cannot be hash_key."""
    with pytest.raises(ValueError, match="cannot be a hash_key"):
        S3Attribute(bucket="bucket", hash_key=True)


def test_s3attribute_cannot_be_range_key():
    """S3Attribute cannot be range_key."""
    with pytest.raises(ValueError, match="cannot be a hash_key or range_key"):
        S3Attribute(bucket="bucket", range_key=True)


def test_s3attribute_serialize_none():
    """S3Attribute.serialize(None) returns None."""
    attr = S3Attribute(bucket="bucket")

    assert attr.serialize(None) is None


def test_s3attribute_serialize_s3value():
    """S3Attribute.serialize(S3Value) returns metadata dict."""
    mock_ops = MagicMock()
    value = S3Value(
        bucket="my-bucket",
        key="path/file.txt",
        size=1024,
        etag="abc123",
        content_type="text/plain",
        s3_ops=mock_ops,
        last_modified="2025-01-05T10:00:00Z",
        version_id="v1",
        metadata={"env": "prod"},
    )

    attr = S3Attribute(bucket="bucket")
    result = attr.serialize(value)

    assert result == {
        "bucket": "my-bucket",
        "key": "path/file.txt",
        "size": 1024,
        "etag": "abc123",
        "content_type": "text/plain",
        "last_modified": "2025-01-05T10:00:00Z",
        "version_id": "v1",
        "metadata": {"env": "prod"},
    }


def test_s3attribute_serialize_s3value_minimal():
    """S3Attribute.serialize(S3Value) omits None fields."""
    mock_ops = MagicMock()
    value = S3Value(
        bucket="bucket",
        key="key",
        size=100,
        etag="etag",
        content_type=None,
        s3_ops=mock_ops,
    )

    attr = S3Attribute(bucket="bucket")
    result = attr.serialize(value)

    assert result == {
        "bucket": "bucket",
        "key": "key",
        "size": 100,
        "etag": "etag",
    }
    assert "content_type" not in result
    assert "last_modified" not in result


def test_s3attribute_serialize_s3file_raises():
    """S3Attribute.serialize(S3File) raises error."""
    attr = S3Attribute(bucket="bucket")
    f = S3File(b"data", name="test.txt")

    with pytest.raises(ValueError, match="must be uploaded before serialization"):
        attr.serialize(f)


def test_s3attribute_deserialize_none():
    """S3Attribute.deserialize(None) returns None."""
    attr = S3Attribute(bucket="bucket")

    assert attr.deserialize(None) is None


def test_s3attribute_deserialize_dict():
    """S3Attribute.deserialize(dict) returns S3Value."""
    attr = S3Attribute(bucket="bucket")
    attr._s3_ops = MagicMock()

    data = {
        "bucket": "my-bucket",
        "key": "path/file.txt",
        "size": 1024,
        "etag": "abc123",
        "content_type": "text/plain",
        "last_modified": "2025-01-05T10:00:00Z",
        "version_id": "v1",
        "metadata": {"env": "prod"},
    }

    result = attr.deserialize(data)

    assert isinstance(result, S3Value)
    assert result.bucket == "my-bucket"
    assert result.key == "path/file.txt"
    assert result.size == 1024
    assert result.etag == "abc123"
    assert result.content_type == "text/plain"
    assert result.last_modified == "2025-01-05T10:00:00Z"
    assert result.version_id == "v1"
    assert result.metadata == {"env": "prod"}


def test_s3attribute_region_override():
    """S3Attribute can override region."""
    attr = S3Attribute(bucket="bucket", region="eu-west-1")

    assert attr.region == "eu-west-1"
