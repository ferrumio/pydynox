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
mod errors;
mod serialization;

use client::DynamoClient;
use serialization::{dynamo_to_py_py, item_from_dynamo, item_to_dynamo, py_to_dynamo_py};

/// Python module for pydynox's Rust core.
///
/// This module is imported as `pydynox_core` in Python and provides
/// the low-level DynamoDB client implementation.
#[pymodule]
fn pydynox_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<DynamoClient>()?;

    // Serialization functions
    m.add_function(wrap_pyfunction!(py_to_dynamo_py, m)?)?;
    m.add_function(wrap_pyfunction!(dynamo_to_py_py, m)?)?;
    m.add_function(wrap_pyfunction!(item_to_dynamo, m)?)?;
    m.add_function(wrap_pyfunction!(item_from_dynamo, m)?)?;

    Ok(())
}
