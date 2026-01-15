"""Memory tests for compression operations.

Tests compress/decompress with large payloads to detect memory leaks
from zstd/lz4 buffer allocations.
"""

import pytest
from pydynox._internal._compression import (
    CompressionAlgorithm,
    compress,
    compress_string,
    decompress,
    decompress_string,
)


@pytest.mark.benchmark
@pytest.mark.parametrize(
    "algorithm",
    [
        pytest.param(CompressionAlgorithm.Zstd, id="zstd"),
        pytest.param(CompressionAlgorithm.Lz4, id="lz4"),
        pytest.param(CompressionAlgorithm.Gzip, id="gzip"),
    ],
)
def test_compress_large_payload(algorithm):
    """Compress large payloads - should not leak memory."""
    # GIVEN a 100KB payload
    data = b"hello world " * 8500

    # WHEN compressing repeatedly in a loop
    for _ in range(100):
        compressed = compress(data, algorithm)
        # THEN compressed data should be smaller than original
        assert len(compressed) < len(data)


@pytest.mark.benchmark
@pytest.mark.parametrize(
    "algorithm",
    [
        pytest.param(CompressionAlgorithm.Zstd, id="zstd"),
        pytest.param(CompressionAlgorithm.Lz4, id="lz4"),
        pytest.param(CompressionAlgorithm.Gzip, id="gzip"),
    ],
)
def test_decompress_large_payload(algorithm):
    """Decompress large payloads - should not leak memory."""
    # GIVEN a compressed 100KB payload
    data = b"hello world " * 8500
    compressed = compress(data, algorithm)

    # WHEN decompressing repeatedly in a loop
    for _ in range(100):
        result = decompress(compressed, algorithm)
        # THEN result should match original data
        assert result == data


@pytest.mark.benchmark
@pytest.mark.parametrize(
    "algorithm",
    [
        pytest.param(CompressionAlgorithm.Zstd, id="zstd"),
        pytest.param(CompressionAlgorithm.Lz4, id="lz4"),
        pytest.param(CompressionAlgorithm.Gzip, id="gzip"),
    ],
)
def test_compress_decompress_roundtrip(algorithm):
    """Compress and decompress in a loop - should not leak memory."""
    # GIVEN a 50KB payload
    data = b"test data for compression " * 2000

    # WHEN compressing and decompressing repeatedly
    for _ in range(100):
        compressed = compress(data, algorithm)
        result = decompress(compressed, algorithm)
        # THEN result should match original data
        assert result == data


@pytest.mark.benchmark
def test_compress_string_large():
    """Compress large strings - should not leak memory."""
    # GIVEN a 100KB string
    data = "hello world " * 8500

    # WHEN compressing repeatedly in a loop
    for _ in range(100):
        compressed = compress_string(data, min_size=10)
        # THEN compressed string should have ZSTD prefix
        assert compressed.startswith("ZSTD:")


@pytest.mark.benchmark
def test_decompress_string_large():
    """Decompress large strings - should not leak memory."""
    # GIVEN a compressed 100KB string
    data = "hello world " * 8500
    compressed = compress_string(data, min_size=10)

    # WHEN decompressing repeatedly in a loop
    for _ in range(100):
        result = decompress_string(compressed)
        # THEN result should match original data
        assert result == data


@pytest.mark.benchmark
def test_compress_varying_sizes():
    """Compress varying payload sizes - should not leak memory."""
    # WHEN compressing payloads of varying sizes in a loop
    for _ in range(50):
        # Small (1KB)
        small = b"x" * 1000
        compress(small)

        # Medium (50KB)
        medium = b"y" * 50000
        compress(medium)

        # Large (200KB)
        large = b"z" * 200000
        compress(large)
    # THEN memory should not grow (no assertions - memory profiler checks this)
