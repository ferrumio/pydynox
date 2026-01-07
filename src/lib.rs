//! # pydynox
//!
//! A fast DynamoDB ORM for Python with a Rust core.
//!
//! This crate provides the Rust backend for pydynox, handling:
//! - Type serialization between Python and DynamoDB
//! - AWS SDK calls via aws-sdk-dynamodb
//! - Async operations with tokio runtime
//!
//! The Python bindings are exposed via PyO3.

use pyo3::prelude::*;

mod basic_operations;
mod batch_operations;
mod client;
mod client_internal;
mod compression;
mod conversions;
mod diagnostics;
mod errors;
mod generators;
mod kms;
mod metrics;
pub mod rate_limiter;
mod s3;
mod serialization;
mod table_operations;
mod tracing;
mod transaction_operations;

use client::DynamoDBClient;
use rate_limiter::{AdaptiveRate, FixedRate, RateLimitMetrics};
use serialization::{dynamo_to_py_py, item_from_dynamo, item_to_dynamo, py_to_dynamo_py};

/// Python module for pydynox's Rust core.
///
/// **WARNING: This is an internal module. Do not import directly.**
///
/// Use `from pydynox import ...` instead. This module is the bridge between
/// Python and Rust.
///
/// **This is NOT part of the public API.** We may introduce breaking changes
/// to this module at any time without prior notice. If you import from
/// `pydynox.pydynox_core` directly, your code may break on any update.
#[pymodule]
fn pydynox_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<DynamoDBClient>()?;

    // Rate limiter classes
    m.add_class::<FixedRate>()?;
    m.add_class::<AdaptiveRate>()?;
    m.add_class::<RateLimitMetrics>()?;

    // Serialization functions
    m.add_function(wrap_pyfunction!(py_to_dynamo_py, m)?)?;
    m.add_function(wrap_pyfunction!(dynamo_to_py_py, m)?)?;
    m.add_function(wrap_pyfunction!(item_to_dynamo, m)?)?;
    m.add_function(wrap_pyfunction!(item_from_dynamo, m)?)?;

    // Register exception classes
    errors::register_exceptions(m)?;

    // Register compression functions
    compression::register_compression(m)?;

    // Register KMS encryption classes
    kms::register_kms(m)?;

    // Register metrics class
    metrics::register_metrics(m)?;

    // Register tracing functions
    tracing::register_tracing(m)?;

    // Register generator functions
    generators::register_generators(m)?;

    // Register S3 operations
    s3::register_s3(m)?;

    // Register diagnostics (hot partition tracker, etc.)
    diagnostics::register_hot_partition(m)?;

    Ok(())
}
