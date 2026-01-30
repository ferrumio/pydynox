"""Compressed attribute type."""

from __future__ import annotations

from typing import Any

from pydynox._internal._compression import (
    CompressionAlgorithm,
    compress_string,
    decompress_string,
)
from pydynox.attributes.base import Attribute


class CompressedAttribute(Attribute[str]):
    """Attribute that auto-compresses large text values.

    Stores data as base64-encoded compressed binary in DynamoDB.
    Compression happens automatically on save, decompression on load.
    All heavy work (compression + base64) is done in Rust for speed.

    Args:
        algorithm: Compression algorithm to use. Options:
            - CompressionAlgorithm.Zstd (default): Best compression ratio
            - CompressionAlgorithm.Lz4: Fastest
            - CompressionAlgorithm.Gzip: Good balance
        level: Compression level. Higher = smaller but slower.
            - zstd: 1-22 (default 3)
            - gzip: 0-9 (default 6)
            - lz4: ignored
        min_size: Minimum size in bytes to compress (default 100).
            Smaller values are stored as-is.
        threshold: Compression ratio threshold (default 0.9).
            Only compress if result is smaller by this ratio.
        partition_key: True if this is the partition key.
        sort_key: True if this is the sort key.
        default: Default value when not provided.
        required: Whether this field is required.

    Example:
        >>> from pydynox import Model, ModelConfig
        >>> from pydynox.attributes import StringAttribute, CompressedAttribute
        >>>
        >>> class Document(Model):
        ...     model_config = ModelConfig(table="documents")
        ...     pk = StringAttribute(partition_key=True)
        ...     body = CompressedAttribute()  # Uses zstd by default
        ...     logs = CompressedAttribute(algorithm=CompressionAlgorithm.Lz4)
    """

    attr_type = "S"  # Stored as base64 string

    def __init__(
        self,
        algorithm: CompressionAlgorithm | None = None,
        level: int | None = None,
        min_size: int = 100,
        threshold: float = 0.9,
        partition_key: bool = False,
        sort_key: bool = False,
        default: str | None = None,
        required: bool = False,
    ):
        """Create a compressed attribute.

        Args:
            algorithm: Compression algorithm (default: zstd).
            level: Compression level.
            min_size: Minimum bytes to trigger compression.
            threshold: Only compress if ratio is below this.
            partition_key: True if this is the partition key.
            sort_key: True if this is the sort key.
            default: Default value when not provided.
            required: Whether this field is required.
        """
        super().__init__(
            partition_key=partition_key,
            sort_key=sort_key,
            default=default,
            required=required,
        )
        self.algorithm = algorithm
        self.level = level
        self.min_size = min_size
        self.threshold = threshold

    def serialize(self, value: str | None) -> str | None:
        """Compress and encode value for DynamoDB.

        Args:
            value: String to compress.

        Returns:
            Base64-encoded compressed data with prefix, or original if
            compression not worthwhile.
        """
        if value is None:
            return None

        # All done in Rust: compression + base64 + prefix
        return compress_string(
            value,
            self.algorithm,
            self.level,
            self.min_size,
            self.threshold,
        )

    def deserialize(self, value: Any) -> str | None:
        """Decompress value from DynamoDB.

        Args:
            value: Stored value (may be compressed or plain).

        Returns:
            Original string.
        """
        if value is None:
            return None

        if not isinstance(value, str):
            return str(value)

        # All done in Rust: detect prefix + base64 decode + decompress
        return decompress_string(value)
