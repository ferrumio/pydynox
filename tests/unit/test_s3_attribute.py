"""Unit tests for S3Attribute."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pydynox._internal._s3 import S3File, S3Value
from pydynox.attributes.s3 import S3Attribute


def test_s3file_from_bytes():
    """S3File can be created from bytes."""
    # WHEN we create S3File from bytes
    data = b"hello world"
    f = S3File(data, name="test.txt")

    # THEN properties should be set correctly
    assert f.data == data
    assert f.name == "test.txt"
    assert f.size == 11
    assert f.content_type is None
    assert f.metadata is None


def test_s3file_from_bytes_with_content_type():
    """S3File accepts content_type."""
    # WHEN we create S3File with content_type
    f = S3File(b"data", name="doc.pdf", content_type="application/pdf")

    # THEN content_type should be set
    assert f.content_type == "application/pdf"


def test_s3file_from_bytes_with_metadata():
    """S3File accepts metadata."""
    # WHEN we create S3File with metadata
    f = S3File(b"data", name="doc.pdf", metadata={"env": "prod", "version": "1"})

    # THEN metadata should be set
    assert f.metadata == {"env": "prod", "version": "1"}


def test_s3file_from_bytes_requires_name():
    """S3File from bytes requires name."""
    # WHEN we try to create S3File without name
    # THEN ValueError should be raised
    with pytest.raises(ValueError, match="name is required"):
        S3File(b"data")


def test_s3file_from_path(tmp_path):
    """S3File can be created from Path."""
    # GIVEN a file on disk
    file_path = tmp_path / "test.txt"
    file_path.write_bytes(b"file content")

    # WHEN we create S3File from Path
    f = S3File(file_path)

    # THEN data and name should be set from file
    assert f.data == b"file content"
    assert f.name == "test.txt"
    assert f.size == 12


def test_s3file_from_path_with_custom_name(tmp_path):
    """S3File from Path can override name."""
    # GIVEN a file on disk
    file_path = tmp_path / "original.txt"
    file_path.write_bytes(b"data")

    # WHEN we create S3File with custom name
    f = S3File(file_path, name="custom.txt")

    # THEN custom name should be used
    assert f.name == "custom.txt"


def test_s3value_properties():
    """S3Value exposes all properties."""
    # WHEN we create S3Value with all properties
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

    # THEN all properties should be accessible
    assert v.bucket == "my-bucket"
    assert v.key == "path/to/file.txt"
    assert v.size == 1024
    assert v.etag == "abc123"
    assert v.content_type == "text/plain"
    assert v.last_modified == "2025-01-05T10:00:00Z"
    assert v.version_id == "v1"
    assert v.metadata == {"key": "value"}


def test_s3value_sync_get_bytes():
    """S3Value.sync_get_bytes() calls s3_ops.sync_download_bytes."""
    # GIVEN an S3Value with mock ops
    mock_ops = MagicMock()
    # sync_download_bytes returns (bytes, S3Metrics)
    mock_metrics = MagicMock()
    mock_ops.sync_download_bytes.return_value = (b"downloaded data", mock_metrics)

    v = S3Value(
        bucket="bucket",
        key="key",
        size=100,
        etag="etag",
        content_type=None,
        s3_ops=mock_ops,
    )

    # WHEN we call sync_get_bytes
    result = v.sync_get_bytes()

    # THEN sync_download_bytes should be called
    assert result == b"downloaded data"
    mock_ops.sync_download_bytes.assert_called_once_with("bucket", "key")


def test_s3value_sync_save_to():
    """S3Value.sync_save_to() calls s3_ops.sync_save_to_file."""
    # GIVEN an S3Value with mock ops
    mock_ops = MagicMock()
    v = S3Value(
        bucket="bucket",
        key="key",
        size=100,
        etag="etag",
        content_type=None,
        s3_ops=mock_ops,
    )

    # WHEN we call sync_save_to
    v.sync_save_to("/tmp/output.txt")

    # THEN sync_save_to_file should be called
    mock_ops.sync_save_to_file.assert_called_once_with("bucket", "key", "/tmp/output.txt")


def test_s3value_sync_save_to_path_object():
    """S3Value.sync_save_to() accepts Path object."""
    # GIVEN an S3Value with mock ops
    mock_ops = MagicMock()
    v = S3Value(
        bucket="bucket",
        key="key",
        size=100,
        etag="etag",
        content_type=None,
        s3_ops=mock_ops,
    )

    # WHEN we call sync_save_to with Path
    v.sync_save_to(Path("/tmp/output.txt"))

    # THEN sync_save_to_file should be called with string path
    mock_ops.sync_save_to_file.assert_called_once_with("bucket", "key", "/tmp/output.txt")


def test_s3value_sync_presigned_url():
    """S3Value.sync_presigned_url() calls s3_ops.sync_presigned_url."""
    # GIVEN an S3Value with mock ops
    mock_ops = MagicMock()
    # sync_presigned_url returns (url, S3Metrics)
    mock_metrics = MagicMock()
    mock_ops.sync_presigned_url.return_value = ("https://presigned.url", mock_metrics)

    v = S3Value(
        bucket="bucket",
        key="key",
        size=100,
        etag="etag",
        content_type=None,
        s3_ops=mock_ops,
    )

    # WHEN we call sync_presigned_url
    result = v.sync_presigned_url(7200)

    # THEN sync_presigned_url should be called with expiry
    assert result == "https://presigned.url"
    mock_ops.sync_presigned_url.assert_called_once_with("bucket", "key", 7200)


def test_s3value_sync_presigned_url_default_expiry():
    """S3Value.sync_presigned_url() defaults to 3600 seconds."""
    # GIVEN an S3Value with mock ops
    mock_ops = MagicMock()
    # sync_presigned_url returns (url, S3Metrics)
    mock_metrics = MagicMock()
    mock_ops.sync_presigned_url.return_value = ("https://presigned.url", mock_metrics)

    v = S3Value(
        bucket="bucket",
        key="key",
        size=100,
        etag="etag",
        content_type=None,
        s3_ops=mock_ops,
    )

    # WHEN we call sync_presigned_url without expiry
    v.sync_presigned_url()

    # THEN default expiry should be 3600
    mock_ops.sync_presigned_url.assert_called_once_with("bucket", "key", 3600)


def test_s3value_repr():
    """S3Value has readable repr."""
    # GIVEN an S3Value
    mock_ops = MagicMock()
    v = S3Value(
        bucket="my-bucket",
        key="path/file.txt",
        size=1024,
        etag="etag",
        content_type=None,
        s3_ops=mock_ops,
    )

    # THEN repr should be readable
    assert repr(v) == "S3Value(bucket='my-bucket', key='path/file.txt', size=1024)"


def test_s3attribute_init():
    """S3Attribute stores bucket and prefix."""
    # WHEN we create S3Attribute
    attr = S3Attribute(bucket="my-bucket", prefix="docs/")

    # THEN bucket and prefix should be stored
    assert attr.bucket == "my-bucket"
    assert attr.prefix == "docs/"


def test_s3attribute_prefix_normalized():
    """S3Attribute normalizes prefix to end with /."""
    # WHEN we create S3Attribute with prefix without trailing /
    attr = S3Attribute(bucket="bucket", prefix="path/to/files")

    # THEN prefix should be normalized
    assert attr.prefix == "path/to/files/"


def test_s3attribute_empty_prefix():
    """S3Attribute handles empty prefix."""
    # WHEN we create S3Attribute without prefix
    attr = S3Attribute(bucket="bucket")

    # THEN prefix should be empty string
    assert attr.prefix == ""


def test_s3attribute_cannot_be_hash_key():
    """S3Attribute cannot be hash_key."""
    # WHEN we try to create S3Attribute as hash_key
    # THEN ValueError should be raised
    with pytest.raises(ValueError, match="cannot be a hash_key"):
        S3Attribute(bucket="bucket", hash_key=True)


def test_s3attribute_cannot_be_range_key():
    """S3Attribute cannot be range_key."""
    # WHEN we try to create S3Attribute as range_key
    # THEN ValueError should be raised
    with pytest.raises(ValueError, match="cannot be a hash_key or range_key"):
        S3Attribute(bucket="bucket", range_key=True)


def test_s3attribute_serialize_none():
    """S3Attribute.serialize(None) returns None."""
    # GIVEN an S3Attribute
    attr = S3Attribute(bucket="bucket")

    # WHEN we serialize None
    # THEN None should be returned
    assert attr.serialize(None) is None


def test_s3attribute_serialize_s3value():
    """S3Attribute.serialize(S3Value) returns metadata dict."""
    # GIVEN an S3Value
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

    # WHEN we serialize
    result = attr.serialize(value)

    # THEN metadata dict should be returned
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
    # GIVEN an S3Value with minimal fields
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

    # WHEN we serialize
    result = attr.serialize(value)

    # THEN None fields should be omitted
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
    # GIVEN an S3File (not uploaded yet)
    attr = S3Attribute(bucket="bucket")
    f = S3File(b"data", name="test.txt")

    # WHEN we try to serialize
    # THEN ValueError should be raised
    with pytest.raises(ValueError, match="must be uploaded before serialization"):
        attr.serialize(f)


def test_s3attribute_deserialize_none():
    """S3Attribute.deserialize(None) returns None."""
    # GIVEN an S3Attribute
    attr = S3Attribute(bucket="bucket")

    # WHEN we deserialize None
    # THEN None should be returned
    assert attr.deserialize(None) is None


def test_s3attribute_deserialize_dict():
    """S3Attribute.deserialize(dict) returns S3Value."""
    # GIVEN an S3Attribute with mock ops
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

    # WHEN we deserialize
    result = attr.deserialize(data)

    # THEN S3Value should be returned with correct properties
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
    # WHEN we create S3Attribute with region
    attr = S3Attribute(bucket="bucket", region="eu-west-1")

    # THEN region should be set
    assert attr.region == "eu-west-1"


# ========== ASYNC TESTS ==========


@pytest.mark.asyncio
async def test_s3value_get_bytes_async():
    """S3Value.get_bytes() async calls s3_ops.download_bytes."""
    # GIVEN an S3Value with mock ops
    mock_ops = MagicMock()
    mock_metrics = MagicMock()

    # Mock the async method
    async def mock_download_bytes(bucket, key):
        return (b"async downloaded data", mock_metrics)

    mock_ops.download_bytes = mock_download_bytes

    v = S3Value(
        bucket="bucket",
        key="key",
        size=100,
        etag="etag",
        content_type=None,
        s3_ops=mock_ops,
    )

    # WHEN we call get_bytes (async)
    result = await v.get_bytes()

    # THEN data should be returned
    assert result == b"async downloaded data"


@pytest.mark.asyncio
async def test_s3value_save_to_async():
    """S3Value.save_to() async calls s3_ops.save_to_file."""
    # GIVEN an S3Value with mock ops
    mock_ops = MagicMock()
    called_with = {}

    async def mock_save_to_file(bucket, key, path):
        called_with["bucket"] = bucket
        called_with["key"] = key
        called_with["path"] = path

    mock_ops.save_to_file = mock_save_to_file

    v = S3Value(
        bucket="bucket",
        key="key",
        size=100,
        etag="etag",
        content_type=None,
        s3_ops=mock_ops,
    )

    # WHEN we call save_to (async)
    await v.save_to("/tmp/output.txt")

    # THEN save_to_file should be called
    assert called_with == {"bucket": "bucket", "key": "key", "path": "/tmp/output.txt"}


@pytest.mark.asyncio
async def test_s3value_save_to_async_path_object():
    """S3Value.save_to() async accepts Path object."""
    # GIVEN an S3Value with mock ops
    mock_ops = MagicMock()
    called_with = {}

    async def mock_save_to_file(bucket, key, path):
        called_with["path"] = path

    mock_ops.save_to_file = mock_save_to_file

    v = S3Value(
        bucket="bucket",
        key="key",
        size=100,
        etag="etag",
        content_type=None,
        s3_ops=mock_ops,
    )

    # WHEN we call save_to with Path (async)
    await v.save_to(Path("/tmp/output.txt"))

    # THEN path should be converted to string
    assert called_with["path"] == "/tmp/output.txt"


@pytest.mark.asyncio
async def test_s3value_presigned_url_async():
    """S3Value.presigned_url() async calls s3_ops.presigned_url."""
    # GIVEN an S3Value with mock ops
    mock_ops = MagicMock()
    mock_metrics = MagicMock()

    async def mock_presigned_url(bucket, key, expires):
        return ("https://async.presigned.url", mock_metrics)

    mock_ops.presigned_url = mock_presigned_url

    v = S3Value(
        bucket="bucket",
        key="key",
        size=100,
        etag="etag",
        content_type=None,
        s3_ops=mock_ops,
    )

    # WHEN we call presigned_url (async)
    result = await v.presigned_url(7200)

    # THEN URL should be returned
    assert result == "https://async.presigned.url"


@pytest.mark.asyncio
async def test_s3value_presigned_url_async_default_expiry():
    """S3Value.presigned_url() async defaults to 3600 seconds."""
    # GIVEN an S3Value with mock ops
    mock_ops = MagicMock()
    mock_metrics = MagicMock()
    called_with = {}

    async def mock_presigned_url(bucket, key, expires):
        called_with["expires"] = expires
        return ("https://presigned.url", mock_metrics)

    mock_ops.presigned_url = mock_presigned_url

    v = S3Value(
        bucket="bucket",
        key="key",
        size=100,
        etag="etag",
        content_type=None,
        s3_ops=mock_ops,
    )

    # WHEN we call presigned_url without expiry (async)
    await v.presigned_url()

    # THEN default expiry should be 3600
    assert called_with["expires"] == 3600


# ========== ADDITIONAL PROPERTY TESTS ==========


def test_s3file_content_type_none():
    """S3File content_type defaults to None."""
    f = S3File(b"data", name="test.txt")
    assert f.content_type is None


def test_s3file_metadata_none():
    """S3File metadata defaults to None."""
    f = S3File(b"data", name="test.txt")
    assert f.metadata is None


def test_s3value_etag_property():
    """S3Value.etag returns the etag."""
    mock_ops = MagicMock()
    v = S3Value(
        bucket="bucket",
        key="key",
        size=100,
        etag="abc123def",
        content_type=None,
        s3_ops=mock_ops,
    )
    assert v.etag == "abc123def"


def test_s3value_size_property():
    """S3Value.size returns the size."""
    mock_ops = MagicMock()
    v = S3Value(
        bucket="bucket",
        key="key",
        size=999,
        etag="etag",
        content_type=None,
        s3_ops=mock_ops,
    )
    assert v.size == 999


def test_s3value_content_type_none():
    """S3Value.content_type can be None."""
    mock_ops = MagicMock()
    v = S3Value(
        bucket="bucket",
        key="key",
        size=100,
        etag="etag",
        content_type=None,
        s3_ops=mock_ops,
    )
    assert v.content_type is None


def test_s3value_last_modified_none():
    """S3Value.last_modified defaults to None."""
    mock_ops = MagicMock()
    v = S3Value(
        bucket="bucket",
        key="key",
        size=100,
        etag="etag",
        content_type=None,
        s3_ops=mock_ops,
    )
    assert v.last_modified is None


def test_s3value_version_id_none():
    """S3Value.version_id defaults to None."""
    mock_ops = MagicMock()
    v = S3Value(
        bucket="bucket",
        key="key",
        size=100,
        etag="etag",
        content_type=None,
        s3_ops=mock_ops,
    )
    assert v.version_id is None


def test_s3value_metadata_none():
    """S3Value.metadata defaults to None."""
    mock_ops = MagicMock()
    v = S3Value(
        bucket="bucket",
        key="key",
        size=100,
        etag="etag",
        content_type=None,
        s3_ops=mock_ops,
    )
    assert v.metadata is None
