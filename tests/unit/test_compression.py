"""Tests for compression module."""

import pytest
from pydynox._internal._compression import (
    CompressionAlgorithm,
    compress,
    compress_string,
    decompress,
    decompress_string,
    should_compress,
)
from pydynox.attributes import CompressedAttribute

# --- Low-level compression functions ---


@pytest.mark.parametrize(
    "algorithm",
    [
        pytest.param(CompressionAlgorithm.Zstd, id="zstd"),
        pytest.param(CompressionAlgorithm.Lz4, id="lz4"),
        pytest.param(CompressionAlgorithm.Gzip, id="gzip"),
    ],
)
def test_compress_decompress_roundtrip(algorithm):
    """Compress and decompress returns original data."""
    # GIVEN original data
    original = b"hello world " * 100

    # WHEN we compress and decompress
    compressed = compress(original, algorithm)
    result = decompress(compressed, algorithm)

    # THEN original data should be restored
    assert result == original


@pytest.mark.parametrize(
    "algorithm",
    [
        pytest.param(CompressionAlgorithm.Zstd, id="zstd"),
        pytest.param(CompressionAlgorithm.Lz4, id="lz4"),
        pytest.param(CompressionAlgorithm.Gzip, id="gzip"),
    ],
)
def test_compression_reduces_size(algorithm):
    """Compression makes data smaller."""
    # GIVEN repetitive data
    original = b"hello world " * 1000

    # WHEN we compress
    compressed = compress(original, algorithm)

    # THEN compressed size should be smaller
    assert len(compressed) < len(original)


def test_compress_default_algorithm():
    """Default algorithm is zstd."""
    # GIVEN original data
    original = b"hello world " * 100

    # WHEN we compress and decompress with defaults
    compressed = compress(original)
    result = decompress(compressed)

    # THEN original data should be restored
    assert result == original


def test_should_compress_large_data():
    """should_compress returns True for large compressible data."""
    # GIVEN large repetitive data
    data = b"hello world " * 1000

    # WHEN we check if it should be compressed
    # THEN it should return True
    assert should_compress(data) is True


def test_should_compress_small_data():
    """should_compress returns False for small data."""
    # GIVEN small data
    data = b"hi"

    # WHEN we check if it should be compressed
    # THEN it should return False
    assert should_compress(data) is False


def test_should_compress_threshold():
    """should_compress respects threshold parameter."""
    # GIVEN data
    data = b"hello world " * 100

    # WHEN we check with a loose threshold
    result_loose = should_compress(data, threshold=0.99)

    # THEN it should return True
    assert result_loose is True


# --- compress_string / decompress_string (Rust fast path) ---


@pytest.mark.parametrize(
    "algorithm",
    [
        pytest.param(CompressionAlgorithm.Zstd, id="zstd"),
        pytest.param(CompressionAlgorithm.Lz4, id="lz4"),
        pytest.param(CompressionAlgorithm.Gzip, id="gzip"),
    ],
)
def test_compress_string_roundtrip(algorithm):
    """compress_string and decompress_string roundtrip works."""
    # GIVEN original string
    original = "hello world " * 100

    # WHEN we compress and decompress
    compressed = compress_string(original, algorithm, min_size=10)
    result = decompress_string(compressed)

    # THEN original string should be restored
    assert result == original


def test_compress_string_small_not_compressed():
    """Small strings are not compressed."""
    # GIVEN a small string
    original = "hi"

    # WHEN we try to compress with high min_size
    result = compress_string(original, min_size=100)

    # THEN it should be unchanged
    assert result == original


def test_compress_string_adds_prefix():
    """Compressed strings have algorithm prefix."""
    # GIVEN a large string
    original = "hello world " * 100

    # WHEN we compress with zstd
    result = compress_string(original, CompressionAlgorithm.Zstd, min_size=10)

    # THEN it should have ZSTD: prefix
    assert result.startswith("ZSTD:")


def test_decompress_string_plain():
    """decompress_string returns plain strings unchanged."""
    # GIVEN a plain string without compression prefix
    plain = "hello world"

    # WHEN we decompress
    result = decompress_string(plain)

    # THEN it should be unchanged
    assert result == plain


# --- CompressedAttribute ---


def test_compressed_attribute_type():
    """CompressedAttribute has string type for base64 storage."""
    # WHEN we create a compressed attribute
    attr = CompressedAttribute()

    # THEN attr_type should be string
    assert attr.attr_type == "S"


def test_compressed_attribute_default_algorithm():
    """Default algorithm is None (Rust uses zstd)."""
    # WHEN we create a compressed attribute without algorithm
    attr = CompressedAttribute()

    # THEN algorithm should be None (Rust defaults to zstd)
    assert attr.algorithm is None


@pytest.mark.parametrize(
    "algorithm",
    [
        pytest.param(CompressionAlgorithm.Zstd, id="zstd"),
        pytest.param(CompressionAlgorithm.Lz4, id="lz4"),
        pytest.param(CompressionAlgorithm.Gzip, id="gzip"),
    ],
)
def test_compressed_attribute_roundtrip(algorithm):
    """Serialize and deserialize returns original value."""
    # GIVEN a compressed attribute and original value
    attr = CompressedAttribute(algorithm=algorithm, min_size=10)
    original = "hello world " * 100

    # WHEN we serialize and deserialize
    serialized = attr.serialize(original)
    result = attr.deserialize(serialized)

    # THEN original value should be restored
    assert result == original


def test_compressed_attribute_small_value_not_compressed():
    """Small values are not compressed."""
    # GIVEN a compressed attribute with high min_size
    attr = CompressedAttribute(min_size=100)
    original = "hi"

    # WHEN we serialize
    serialized = attr.serialize(original)

    # THEN it should be stored as-is without prefix
    assert serialized == original
    assert not serialized.startswith("ZSTD:")


def test_compressed_attribute_large_value_compressed():
    """Large values are compressed with prefix."""
    # GIVEN a compressed attribute with low min_size
    attr = CompressedAttribute(min_size=10)
    original = "hello world " * 100

    # WHEN we serialize
    serialized = attr.serialize(original)

    # THEN it should have compression prefix
    assert serialized.startswith("ZSTD:")


@pytest.mark.parametrize(
    "algorithm,prefix",
    [
        pytest.param(CompressionAlgorithm.Zstd, "ZSTD:", id="zstd"),
        pytest.param(CompressionAlgorithm.Lz4, "LZ4:", id="lz4"),
        pytest.param(CompressionAlgorithm.Gzip, "GZIP:", id="gzip"),
    ],
)
def test_compressed_attribute_prefix(algorithm, prefix):
    """Each algorithm has correct prefix."""
    # GIVEN a compressed attribute with specific algorithm
    attr = CompressedAttribute(algorithm=algorithm, min_size=10)
    original = "hello world " * 100

    # WHEN we serialize
    serialized = attr.serialize(original)

    # THEN it should have the correct prefix
    assert serialized.startswith(prefix)


def test_compressed_attribute_none_value():
    """None values are handled correctly."""
    # GIVEN a compressed attribute
    attr = CompressedAttribute()

    # WHEN we serialize/deserialize None
    # THEN None should be returned
    assert attr.serialize(None) is None
    assert attr.deserialize(None) is None


def test_compressed_attribute_uncompressed_deserialize():
    """Deserialize handles uncompressed values."""
    # GIVEN a compressed attribute and plain value
    attr = CompressedAttribute()
    plain = "hello world"

    # WHEN we deserialize a plain value
    result = attr.deserialize(plain)

    # THEN it should be returned unchanged
    assert result == plain


def test_compressed_attribute_custom_level():
    """Custom compression level works."""
    # GIVEN a compressed attribute with custom level
    attr = CompressedAttribute(level=10, min_size=10)
    original = "hello world " * 100

    # WHEN we serialize and deserialize
    serialized = attr.serialize(original)
    result = attr.deserialize(serialized)

    # THEN original value should be restored
    assert result == original


def test_compressed_attribute_threshold():
    """Threshold controls when compression happens."""
    # GIVEN a compressed attribute with very strict threshold
    attr_strict = CompressedAttribute(threshold=0.01, min_size=10)
    original = "hello world " * 10

    # WHEN we serialize
    serialized = attr_strict.serialize(original)

    # THEN it should not be compressed due to strict threshold
    assert not serialized.startswith("ZSTD:")


def test_compressed_attribute_key_flags():
    """CompressedAttribute supports partition_key and sort_key."""
    # WHEN we create compressed attributes with key flags
    hash_attr = CompressedAttribute(partition_key=True)
    range_attr = CompressedAttribute(sort_key=True)

    # THEN key flags should be set correctly
    assert hash_attr.partition_key is True
    assert hash_attr.sort_key is False
    assert range_attr.partition_key is False
    assert range_attr.sort_key is True
