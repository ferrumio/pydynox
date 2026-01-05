//! KMS encrypt/decrypt operations.

use crate::errors::{map_kms_error, EncryptionError};
use crate::kms::ENCRYPTED_PREFIX;
use aws_sdk_kms::primitives::Blob;
use aws_sdk_kms::Client;
use base64::{engine::general_purpose::STANDARD as BASE64, Engine};
use pyo3::prelude::*;
use std::collections::HashMap;
use std::sync::Arc;
use tokio::runtime::Runtime;

// ========== CORE ASYNC OPERATIONS ==========

/// Core async encrypt operation.
pub async fn execute_encrypt(
    client: Client,
    key_id: String,
    context: HashMap<String, String>,
    plaintext: String,
) -> Result<String, PyErr> {
    let mut req = client
        .encrypt()
        .key_id(&key_id)
        .plaintext(Blob::new(plaintext.as_bytes()));

    for (k, v) in &context {
        req = req.encryption_context(k, v);
    }

    let result = req.send().await;

    match result {
        Ok(output) => {
            let blob = output
                .ciphertext_blob()
                .ok_or_else(|| EncryptionError::new_err("No ciphertext returned from KMS"))?;
            let encoded = BASE64.encode(blob.as_ref());
            Ok(format!("{}{}", ENCRYPTED_PREFIX, encoded))
        }
        Err(e) => Err(map_kms_error(e)),
    }
}

/// Core async decrypt operation.
pub async fn execute_decrypt(
    client: Client,
    context: HashMap<String, String>,
    ciphertext: String,
) -> Result<String, PyErr> {
    // Check for prefix
    let encoded = match ciphertext.strip_prefix(ENCRYPTED_PREFIX) {
        Some(s) => s,
        None => {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "Ciphertext must start with 'ENC:' prefix",
            ));
        }
    };

    // Decode base64
    let decoded = BASE64
        .decode(encoded)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Invalid base64: {}", e)))?;

    let mut req = client.decrypt().ciphertext_blob(Blob::new(decoded));

    for (k, v) in &context {
        req = req.encryption_context(k, v);
    }

    let result = req.send().await;

    match result {
        Ok(output) => {
            let blob = output
                .plaintext()
                .ok_or_else(|| EncryptionError::new_err("No plaintext returned from KMS"))?;
            String::from_utf8(blob.as_ref().to_vec()).map_err(|e| {
                pyo3::exceptions::PyValueError::new_err(format!("Invalid UTF-8: {}", e))
            })
        }
        Err(e) => Err(map_kms_error(e)),
    }
}

// ========== SYNC WRAPPERS ==========

/// Sync encrypt.
pub fn sync_encrypt(
    client: &Client,
    runtime: &Arc<Runtime>,
    key_id: &str,
    context: &HashMap<String, String>,
    plaintext: &str,
) -> PyResult<String> {
    runtime.block_on(execute_encrypt(
        client.clone(),
        key_id.to_string(),
        context.clone(),
        plaintext.to_string(),
    ))
}

/// Sync decrypt.
pub fn sync_decrypt(
    client: &Client,
    runtime: &Arc<Runtime>,
    context: &HashMap<String, String>,
    ciphertext: &str,
) -> PyResult<String> {
    runtime.block_on(execute_decrypt(
        client.clone(),
        context.clone(),
        ciphertext.to_string(),
    ))
}

// ========== ASYNC WRAPPERS ==========

/// Async encrypt - returns Python awaitable.
pub fn async_encrypt<'py>(
    py: Python<'py>,
    client: Client,
    key_id: String,
    context: HashMap<String, String>,
    plaintext: String,
) -> PyResult<Bound<'py, PyAny>> {
    pyo3_async_runtimes::tokio::future_into_py(py, async move {
        execute_encrypt(client, key_id, context, plaintext).await
    })
}

/// Async decrypt - returns Python awaitable.
pub fn async_decrypt<'py>(
    py: Python<'py>,
    client: Client,
    context: HashMap<String, String>,
    ciphertext: String,
) -> PyResult<Bound<'py, PyAny>> {
    pyo3_async_runtimes::tokio::future_into_py(py, async move {
        execute_decrypt(client, context, ciphertext).await
    })
}
