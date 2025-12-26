//! Error types for pydyno.
//!
//! This module defines the error types used throughout pydyno.
//! All errors are converted to Python exceptions via PyO3.

use pyo3::exceptions::PyException;
use pyo3::prelude::*;
use thiserror::Error;

/// Error types for pydyno operations.
///
/// These errors are automatically converted to Python exceptions
/// when returned from PyO3 functions.
#[derive(Error, Debug)]
pub enum PydynoError {
    /// General DynamoDB error from the AWS SDK.
    #[error("DynamoDB error: {0}")]
    DynamoDb(String),

    /// Condition check failed (e.g., optimistic locking failure).
    ///
    /// Raised when a conditional write/delete fails because
    /// the condition expression evaluated to false.
    #[error("Condition check failed: {0}")]
    ConditionCheckFailed(String),

    /// Validation error for a specific field.
    ///
    /// Raised when model validation fails before sending to DynamoDB.
    #[error("Validation error on field '{field}': {message}")]
    Validation {
        /// The field that failed validation.
        field: String,
        /// Description of the validation error.
        message: String,
    },

    /// Table not found in DynamoDB.
    #[error("Table not found: {0}")]
    TableNotFound(String),

    /// Transaction failed.
    ///
    /// Raised when a TransactWriteItems operation fails.
    /// All operations in the transaction are rolled back.
    #[error("Transaction failed: {0}")]
    Transaction(String),

    /// Serialization/deserialization error.
    ///
    /// Raised when converting between Python and DynamoDB types fails.
    #[error("Serialization error: {0}")]
    Serialization(String),
}

impl From<PydynoError> for PyErr {
    /// Convert a PydynoError to a Python exception.
    fn from(err: PydynoError) -> PyErr {
        PyException::new_err(err.to_string())
    }
}
