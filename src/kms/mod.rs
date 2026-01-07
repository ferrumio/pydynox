//! KMS envelope encryption module for field-level encryption.
//!
//! Uses envelope encryption pattern:
//! 1. GenerateDataKey gets a plaintext + encrypted data key
//! 2. Plaintext key encrypts data locally with AES-256-GCM
//! 3. Encrypted key is stored alongside the encrypted data
//!
//! Benefits over direct KMS Encrypt/Decrypt:
//! - No 4KB size limit (DynamoDB fields can be 400KB)
//! - Fewer KMS calls (one per operation, not one per field)
//! - Faster (AES in Rust is much faster than KMS API calls)

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
