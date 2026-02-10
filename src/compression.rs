//! Compression module for DynamoDB attributes.
//!
//! Provides transparent compression for large text attributes to reduce
//! item size and storage costs. Supports multiple algorithms:
//! - [`zstd`]: Best compression ratio (default)
//! - [`lz4`]: Fastest compression/decompression
//! - [`gzip`]: Good balance, widely compatible

use base64::{Engine, engine::general_purpose::STANDARD as BASE64};
use pyo3::prelude::*;
use pyo3::types::PyBytes;
use std::io::{Read, Write};

/// Compression algorithm options.
#[pyclass(eq, eq_int, from_py_object)]
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum CompressionAlgorithm {
    /// Zstandard - best compression ratio
    Zstd = 0,
    /// LZ4 - fastest compression
    Lz4 = 1,
    /// Gzip - widely compatible
    Gzip = 2,
}

impl CompressionAlgorithm {
    fn prefix(&self) -> &'static str {
        match self {
            CompressionAlgorithm::Zstd => "ZSTD:",
            CompressionAlgorithm::Lz4 => "LZ4:",
            CompressionAlgorithm::Gzip => "GZIP:",
        }
    }

    fn from_prefix(s: &str) -> Option<Self> {
        if s.starts_with("ZSTD:") {
            Some(CompressionAlgorithm::Zstd)
        } else if s.starts_with("LZ4:") {
            Some(CompressionAlgorithm::Lz4)
        } else if s.starts_with("GZIP:") {
            Some(CompressionAlgorithm::Gzip)
        } else {
            None
        }
    }
}

/// Compress data using zstd algorithm.
fn compress_zstd(data: &[u8], level: i32) -> PyResult<Vec<u8>> {
    zstd::encode_all(data, level).map_err(|e| {
        pyo3::exceptions::PyRuntimeError::new_err(format!("zstd compression failed: {}", e))
    })
}

/// Decompress zstd data.
fn decompress_zstd(data: &[u8]) -> PyResult<Vec<u8>> {
    zstd::decode_all(data).map_err(|e| {
        pyo3::exceptions::PyRuntimeError::new_err(format!("zstd decompression failed: {}", e))
    })
}

/// Compress data using lz4 algorithm.
fn compress_lz4(data: &[u8]) -> PyResult<Vec<u8>> {
    Ok(lz4_flex::compress_prepend_size(data))
}

/// Decompress lz4 data.
fn decompress_lz4(data: &[u8]) -> PyResult<Vec<u8>> {
    lz4_flex::decompress_size_prepended(data).map_err(|e| {
        pyo3::exceptions::PyRuntimeError::new_err(format!("lz4 decompression failed: {}", e))
    })
}

/// Compress data using gzip algorithm.
fn compress_gzip(data: &[u8], level: u32) -> PyResult<Vec<u8>> {
    let mut encoder = flate2::write::GzEncoder::new(Vec::new(), flate2::Compression::new(level));
    encoder.write_all(data).map_err(|e| {
        pyo3::exceptions::PyRuntimeError::new_err(format!("gzip compression failed: {}", e))
    })?;
    encoder.finish().map_err(|e| {
        pyo3::exceptions::PyRuntimeError::new_err(format!("gzip compression failed: {}", e))
    })
}

/// Decompress gzip data.
fn decompress_gzip(data: &[u8]) -> PyResult<Vec<u8>> {
    let mut decoder = flate2::read::GzDecoder::new(data);
    let mut result = Vec::new();
    decoder.read_to_end(&mut result).map_err(|e| {
        pyo3::exceptions::PyRuntimeError::new_err(format!("gzip decompression failed: {}", e))
    })?;
    Ok(result)
}

fn compress_bytes(
    data: &[u8],
    algo: CompressionAlgorithm,
    level: Option<i32>,
) -> PyResult<Vec<u8>> {
    match algo {
        CompressionAlgorithm::Zstd => compress_zstd(data, level.unwrap_or(3)),
        CompressionAlgorithm::Lz4 => compress_lz4(data),
        CompressionAlgorithm::Gzip => compress_gzip(data, level.unwrap_or(6) as u32),
    }
}

fn decompress_bytes(data: &[u8], algo: CompressionAlgorithm) -> PyResult<Vec<u8>> {
    match algo {
        CompressionAlgorithm::Zstd => decompress_zstd(data),
        CompressionAlgorithm::Lz4 => decompress_lz4(data),
        CompressionAlgorithm::Gzip => decompress_gzip(data),
    }
}

/// Compress bytes using the specified algorithm.
///
/// Args:
///     data: Raw bytes to compress.
///     algorithm: Compression algorithm (default: zstd).
///     level: Compression level. Higher = better compression but slower.
///
/// Returns:
///     Compressed bytes.
#[pyfunction]
#[pyo3(signature = (data, algorithm=None, level=None))]
pub fn compress<'py>(
    py: Python<'py>,
    data: &[u8],
    algorithm: Option<CompressionAlgorithm>,
    level: Option<i32>,
) -> PyResult<Bound<'py, PyBytes>> {
    let algo = algorithm.unwrap_or(CompressionAlgorithm::Zstd);
    let compressed = compress_bytes(data, algo, level)?;
    Ok(PyBytes::new(py, &compressed))
}

/// Decompress bytes using the specified algorithm.
///
/// Args:
///     data: Compressed bytes.
///     algorithm: Compression algorithm used (default: zstd).
///
/// Returns:
///     Original uncompressed bytes.
#[pyfunction]
#[pyo3(signature = (data, algorithm=None))]
pub fn decompress<'py>(
    py: Python<'py>,
    data: &[u8],
    algorithm: Option<CompressionAlgorithm>,
) -> PyResult<Bound<'py, PyBytes>> {
    let algo = algorithm.unwrap_or(CompressionAlgorithm::Zstd);
    let decompressed = decompress_bytes(data, algo)?;
    Ok(PyBytes::new(py, &decompressed))
}

/// Check if compression would save space.
///
/// Args:
///     data: Raw bytes to check.
///     algorithm: Compression algorithm (default: zstd).
///     threshold: Minimum ratio to consider worthwhile (default: 0.9).
///
/// Returns:
///     True if compression is worthwhile.
#[pyfunction]
#[pyo3(signature = (data, algorithm=None, threshold=None))]
pub fn should_compress(
    data: &[u8],
    algorithm: Option<CompressionAlgorithm>,
    threshold: Option<f64>,
) -> PyResult<bool> {
    if data.len() < 100 {
        return Ok(false);
    }

    let algo = algorithm.unwrap_or(CompressionAlgorithm::Zstd);
    let threshold = threshold.unwrap_or(0.9);
    let compressed_len = compress_bytes(data, algo, None)?.len();
    let ratio = compressed_len as f64 / data.len() as f64;
    Ok(ratio < threshold)
}

/// Compress a string and return base64-encoded result with prefix.
///
/// Does compression + base64 encoding in Rust for speed.
/// Returns the original string if compression is not worthwhile.
///
/// Args:
///     value: String to compress.
///     algorithm: Compression algorithm (default: zstd).
///     level: Compression level.
///     min_size: Minimum bytes to trigger compression (default: 100).
///     threshold: Only compress if ratio is below this (default: 0.9).
///
/// Returns:
///     Prefixed base64 string like "ZSTD:abc123..." or original if not compressed.
#[pyfunction]
#[pyo3(signature = (value, algorithm=None, level=None, min_size=None, threshold=None))]
pub fn compress_string(
    value: &str,
    algorithm: Option<CompressionAlgorithm>,
    level: Option<i32>,
    min_size: Option<usize>,
    threshold: Option<f64>,
) -> PyResult<String> {
    let algo = algorithm.unwrap_or(CompressionAlgorithm::Zstd);
    let min_size = min_size.unwrap_or(100);
    let threshold = threshold.unwrap_or(0.9);

    let data = value.as_bytes();

    // Skip small values
    if data.len() < min_size {
        return Ok(value.to_string());
    }

    // Check if compression is worthwhile
    let compressed = compress_bytes(data, algo, level)?;
    let ratio = compressed.len() as f64 / data.len() as f64;

    if ratio >= threshold {
        return Ok(value.to_string());
    }

    // Encode and add prefix
    let encoded = BASE64.encode(&compressed);
    Ok(format!("{}{}", algo.prefix(), encoded))
}

/// Decompress a string that was compressed with compress_string.
///
/// Detects the algorithm from the prefix and decompresses.
/// Returns the original string if not compressed.
///
/// Args:
///     value: Compressed string with prefix, or plain string.
///
/// Returns:
///     Original decompressed string.
#[pyfunction]
pub fn decompress_string(value: &str) -> PyResult<String> {
    // Check for compression prefix
    let algo = match CompressionAlgorithm::from_prefix(value) {
        Some(a) => a,
        None => return Ok(value.to_string()), // Not compressed
    };

    // Remove prefix
    let encoded = &value[algo.prefix().len()..];

    // Decode base64
    let compressed = BASE64
        .decode(encoded)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Invalid base64: {}", e)))?;

    // Decompress
    let decompressed = decompress_bytes(&compressed, algo)?;

    // Convert to string
    String::from_utf8(decompressed)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Invalid UTF-8: {}", e)))
}

/// Register compression functions in the Python module.
pub fn register_compression(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<CompressionAlgorithm>()?;
    m.add_function(wrap_pyfunction!(compress, m)?)?;
    m.add_function(wrap_pyfunction!(decompress, m)?)?;
    m.add_function(wrap_pyfunction!(should_compress, m)?)?;
    m.add_function(wrap_pyfunction!(compress_string, m)?)?;
    m.add_function(wrap_pyfunction!(decompress_string, m)?)?;
    Ok(())
}
