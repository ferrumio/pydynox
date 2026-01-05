"""Internal S3 classes. Do not use directly."""

from __future__ import annotations

from pathlib import Path

from pydynox import pydynox_core

# Re-export Rust classes
S3Operations = pydynox_core.S3Operations
S3Metadata = pydynox_core.S3Metadata


class S3File:
    """Wrapper for data to upload to S3.

    Use this to set S3Attribute values.

    Example:
        doc.content = S3File(b"data", name="report.pdf")
        doc.content = S3File(Path("/path/to/file.pdf"))
    """

    def __init__(
        self,
        data: bytes | Path,
        name: str | None = None,
        content_type: str | None = None,
        metadata: dict[str, str] | None = None,
    ):
        """Create an S3File.

        Args:
            data: Bytes or Path to file.
            name: File name (required if data is bytes).
            content_type: MIME type (optional).
            metadata: User-defined metadata (optional).
        """
        if isinstance(data, Path):
            self._data = data.read_bytes()
            self._name = name or data.name
        else:
            if name is None:
                raise ValueError("name is required when data is bytes")
            self._data = data
            self._name = name

        self._content_type = content_type
        self._metadata = metadata

    @property
    def data(self) -> bytes:
        """Get the file data."""
        return self._data

    @property
    def name(self) -> str:
        """Get the file name."""
        return self._name

    @property
    def content_type(self) -> str | None:
        """Get the content type."""
        return self._content_type

    @property
    def metadata(self) -> dict[str, str] | None:
        """Get user-defined metadata."""
        return self._metadata

    @property
    def size(self) -> int:
        """Get the file size in bytes."""
        return len(self._data)


class S3Value:
    """Reference to a file stored in S3.

    Returned when reading S3Attribute from DynamoDB.
    Provides methods to download or get presigned URL.
    """

    def __init__(
        self,
        bucket: str,
        key: str,
        size: int,
        etag: str,
        content_type: str | None,
        s3_ops: S3Operations,
        last_modified: str | None = None,
        version_id: str | None = None,
        metadata: dict[str, str] | None = None,
    ):
        """Create an S3Value.

        Args:
            bucket: S3 bucket name.
            key: S3 object key.
            size: File size in bytes.
            etag: S3 ETag.
            content_type: MIME type.
            s3_ops: S3Operations instance.
            last_modified: Last modified timestamp (ISO 8601).
            version_id: S3 version ID (if versioning enabled).
            metadata: User-defined metadata.
        """
        self._bucket = bucket
        self._key = key
        self._size = size
        self._etag = etag
        self._content_type = content_type
        self._s3_ops = s3_ops
        self._last_modified = last_modified
        self._version_id = version_id
        self._metadata = metadata

    @property
    def bucket(self) -> str:
        """Get the S3 bucket name."""
        return self._bucket

    @property
    def key(self) -> str:
        """Get the S3 object key."""
        return self._key

    @property
    def size(self) -> int:
        """Get the file size in bytes."""
        return self._size

    @property
    def etag(self) -> str:
        """Get the S3 ETag."""
        return self._etag

    @property
    def content_type(self) -> str | None:
        """Get the content type."""
        return self._content_type

    @property
    def last_modified(self) -> str | None:
        """Get the last modified timestamp (ISO 8601)."""
        return self._last_modified

    @property
    def version_id(self) -> str | None:
        """Get the S3 version ID (if versioning enabled)."""
        return self._version_id

    @property
    def metadata(self) -> dict[str, str] | None:
        """Get user-defined metadata."""
        return self._metadata

    def get_bytes(self) -> bytes:
        """Download the file as bytes.

        Warning: Loads entire file into memory.
        """
        return self._s3_ops.download_bytes(self._bucket, self._key)

    async def async_get_bytes(self) -> bytes:
        """Async download the file as bytes."""
        return await self._s3_ops.async_download_bytes(self._bucket, self._key)

    def save_to(self, path: str | Path) -> None:
        """Download and save to a file (streaming, memory efficient).

        Args:
            path: Path to save the file.
        """
        self._s3_ops.save_to_file(self._bucket, self._key, str(path))

    async def async_save_to(self, path: str | Path) -> None:
        """Async download and save to a file (streaming)."""
        await self._s3_ops.async_save_to_file(self._bucket, self._key, str(path))

    def presigned_url(self, expires: int = 3600) -> str:
        """Generate a presigned URL for download.

        Args:
            expires: URL expiration time in seconds (default 1 hour).

        Returns:
            Presigned URL string.
        """
        return self._s3_ops.presigned_url(self._bucket, self._key, expires)

    async def async_presigned_url(self, expires: int = 3600) -> str:
        """Async generate a presigned URL."""
        return await self._s3_ops.async_presigned_url(self._bucket, self._key, expires)

    def __repr__(self) -> str:
        return f"S3Value(bucket='{self._bucket}', key='{self._key}', size={self._size})"
