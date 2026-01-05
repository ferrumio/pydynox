//! KMS encryption module for field-level encryption.
//!
//! Provides per-field encryption using AWS KMS. The KMS client inherits
//! all config from the DynamoDB client, only allowing region override.

mod client;
mod operations;

pub use client::KmsEncryptor;

use pyo3::prelude::*;

/// Prefix for encrypted values to detect them on read.
pub const ENCRYPTED_PREFIX: &str = "ENC:";

/// Register KMS classes in the Python module.
pub fn register_kms(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<KmsEncryptor>()?;
    Ok(())
}
