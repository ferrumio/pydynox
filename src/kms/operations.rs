//! KMS envelope encryption operations.
//!
//! Uses GenerateDataKey for envelope encryption:
//! 1. Generate a data key with KMS (one call)
//! 2. Encrypt data locally with AES-GCM (fast, no size limit)
//! 3. Store encrypted data + encrypted DEK together
//!
//! This solves two problems:
//! - KMS Encrypt has 4KB limit, but DynamoDB fields can be 400KB
//! - Reduces KMS calls (one per operation instead of one per field)

use crate::errors::{map_kms_error, EncryptionException};
use crate::kms::ENCRYPTED_PREFIX;
use aes_gcm::{
    aead::{Aead, KeyInit},
    Aes256Gcm, Nonce,
};
use aws_sdk_kms::primitives::Blob;
use aws_sdk_kms::types::DataKeySpec;
use aws_sdk_kms::Client;
use base64::{engine::general_purpose::STANDARD as BASE64, Engine};
use pyo3::prelude::*;
use rand::RngCore;
use std::collections::HashMap;
use std::sync::Arc;
use std::time::Instant;
use tokio::runtime::Runtime;

/// Storage format version for future compatibility.
const FORMAT_VERSION: u8 = 1;

/// Nonce size for AES-GCM (96 bits = 12 bytes).
const NONCE_SIZE: usize = 12;

/// Metrics from a KMS operation.
#[pyclass]
#[derive(Clone, Debug, Default)]
pub struct KmsMetrics {
    /// Total duration in milliseconds.
    #[pyo3(get)]
    pub duration_ms: f64,

    /// Number of KMS API calls made.
    #[pyo3(get)]
    pub kms_calls: u32,
}

#[pymethods]
impl KmsMetrics {
    #[new]
    #[pyo3(signature = (duration_ms=0.0, kms_calls=0))]
    pub fn new(duration_ms: f64, kms_calls: u32) -> Self {
        Self {
            duration_ms,
            kms_calls,
        }
    }

    fn __repr__(&self) -> String {
        format!(
            "KmsMetrics(duration_ms={:.2}, kms_calls={})",
            self.duration_ms, self.kms_calls
        )
    }
}

/// Result of an encrypt operation with metrics.
#[pyclass]
#[derive(Clone, Debug)]
pub struct EncryptResult {
    /// The encrypted ciphertext.
    #[pyo3(get)]
    pub ciphertext: String,

    /// Metrics from the operation.
    #[pyo3(get)]
    pub metrics: KmsMetrics,
}

/// Result of a decrypt operation with metrics.
#[pyclass]
#[derive(Clone, Debug)]
pub struct DecryptResult {
    /// The decrypted plaintext.
    #[pyo3(get)]
    pub plaintext: String,

    /// Metrics from the operation.
    #[pyo3(get)]
    pub metrics: KmsMetrics,
}

// ========== LOCAL AES OPERATIONS ==========

/// Encrypt data locally using AES-256-GCM.
///
/// Returns: nonce (12 bytes) + ciphertext
fn encrypt_local(plaintext: &[u8], key: &[u8]) -> Result<Vec<u8>, PyErr> {
    let cipher = Aes256Gcm::new_from_slice(key)
        .map_err(|e| EncryptionException::new_err(format!("Invalid key: {}", e)))?;

    // Generate random nonce
    let mut nonce_bytes = [0u8; NONCE_SIZE];
    rand::rng().fill_bytes(&mut nonce_bytes);
    let nonce = Nonce::from_slice(&nonce_bytes);

    // Encrypt
    let ciphertext = cipher
        .encrypt(nonce, plaintext)
        .map_err(|e| EncryptionException::new_err(format!("Encryption failed: {}", e)))?;

    // Prepend nonce to ciphertext
    let mut result = Vec::with_capacity(NONCE_SIZE + ciphertext.len());
    result.extend_from_slice(&nonce_bytes);
    result.extend_from_slice(&ciphertext);
    Ok(result)
}

/// Decrypt data locally using AES-256-GCM.
///
/// Expects: nonce (12 bytes) + ciphertext
fn decrypt_local(data: &[u8], key: &[u8]) -> Result<Vec<u8>, PyErr> {
    if data.len() < NONCE_SIZE {
        return Err(EncryptionException::new_err(
            "Data too short for decryption",
        ));
    }

    let cipher = Aes256Gcm::new_from_slice(key)
        .map_err(|e| EncryptionException::new_err(format!("Invalid key: {}", e)))?;

    let (nonce_bytes, ciphertext) = data.split_at(NONCE_SIZE);
    let nonce = Nonce::from_slice(nonce_bytes);

    cipher
        .decrypt(nonce, ciphertext)
        .map_err(|e| EncryptionException::new_err(format!("Decryption failed: {}", e)))
}

// ========== STORAGE FORMAT ==========

/// Pack encrypted data for storage.
///
/// Format: version (1 byte) + dek_len (2 bytes) + encrypted_dek + encrypted_data
fn pack_envelope(encrypted_dek: &[u8], encrypted_data: &[u8]) -> Vec<u8> {
    let dek_len = encrypted_dek.len() as u16;
    let mut result = Vec::with_capacity(3 + encrypted_dek.len() + encrypted_data.len());
    result.push(FORMAT_VERSION);
    result.extend_from_slice(&dek_len.to_be_bytes());
    result.extend_from_slice(encrypted_dek);
    result.extend_from_slice(encrypted_data);
    result
}

/// Unpack encrypted data from storage.
///
/// Returns: (encrypted_dek, encrypted_data)
fn unpack_envelope(data: &[u8]) -> Result<(&[u8], &[u8]), PyErr> {
    if data.len() < 3 {
        return Err(EncryptionException::new_err("Invalid envelope: too short"));
    }

    let version = data[0];
    if version != FORMAT_VERSION {
        return Err(EncryptionException::new_err(format!(
            "Unsupported envelope version: {}",
            version
        )));
    }

    let dek_len = u16::from_be_bytes([data[1], data[2]]) as usize;
    if data.len() < 3 + dek_len {
        return Err(EncryptionException::new_err(
            "Invalid envelope: truncated DEK",
        ));
    }

    let encrypted_dek = &data[3..3 + dek_len];
    let encrypted_data = &data[3 + dek_len..];
    Ok((encrypted_dek, encrypted_data))
}

// ========== CORE ASYNC OPERATIONS ==========

/// Encrypt using envelope encryption.
///
/// 1. Call KMS GenerateDataKey to get plaintext + encrypted DEK
/// 2. Use plaintext DEK to AES encrypt locally
/// 3. Pack encrypted DEK + encrypted data together
///
/// Returns: (ciphertext, metrics)
pub async fn execute_encrypt(
    client: Client,
    key_id: String,
    context: HashMap<String, String>,
    plaintext: String,
) -> Result<(String, KmsMetrics), PyErr> {
    let start = Instant::now();

    // Generate data key
    let mut req = client
        .generate_data_key()
        .key_id(&key_id)
        .key_spec(DataKeySpec::Aes256);

    for (k, v) in &context {
        req = req.encryption_context(k, v);
    }

    let result = req.send().await;

    match result {
        Ok(output) => {
            // Get plaintext key (for local encryption)
            let plaintext_key = output
                .plaintext()
                .ok_or_else(|| EncryptionException::new_err("No plaintext key from KMS"))?;

            // Get encrypted key (to store with data)
            let encrypted_key = output
                .ciphertext_blob()
                .ok_or_else(|| EncryptionException::new_err("No encrypted key from KMS"))?;

            // Encrypt data locally with plaintext key
            let encrypted_data = encrypt_local(plaintext.as_bytes(), plaintext_key.as_ref())?;

            // Pack envelope: encrypted_dek + encrypted_data
            let envelope = pack_envelope(encrypted_key.as_ref(), &encrypted_data);

            // Encode and add prefix
            let encoded = BASE64.encode(&envelope);
            let ciphertext = format!("{}{}", ENCRYPTED_PREFIX, encoded);

            let metrics = KmsMetrics {
                duration_ms: start.elapsed().as_secs_f64() * 1000.0,
                kms_calls: 1, // GenerateDataKey
            };

            Ok((ciphertext, metrics))
        }
        Err(e) => Err(map_kms_error(e)),
    }
}

/// Decrypt using envelope encryption.
///
/// 1. Unpack encrypted DEK + encrypted data
/// 2. Call KMS Decrypt to get plaintext DEK
/// 3. Use plaintext DEK to AES decrypt locally
///
/// Returns: (plaintext, metrics)
pub async fn execute_decrypt(
    client: Client,
    context: HashMap<String, String>,
    ciphertext: String,
) -> Result<(String, KmsMetrics), PyErr> {
    let start = Instant::now();

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
    let envelope = BASE64
        .decode(encoded)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Invalid base64: {}", e)))?;

    // Unpack envelope
    let (encrypted_dek, encrypted_data) = unpack_envelope(&envelope)?;

    // Decrypt DEK with KMS
    let mut req = client
        .decrypt()
        .ciphertext_blob(Blob::new(encrypted_dek.to_vec()));

    for (k, v) in &context {
        req = req.encryption_context(k, v);
    }

    let result = req.send().await;

    match result {
        Ok(output) => {
            let plaintext_key = output
                .plaintext()
                .ok_or_else(|| EncryptionException::new_err("No plaintext key from KMS"))?;

            // Decrypt data locally
            let plaintext_bytes = decrypt_local(encrypted_data, plaintext_key.as_ref())?;

            let plaintext = String::from_utf8(plaintext_bytes).map_err(|e| {
                pyo3::exceptions::PyValueError::new_err(format!("Invalid UTF-8: {}", e))
            })?;

            let metrics = KmsMetrics {
                duration_ms: start.elapsed().as_secs_f64() * 1000.0,
                kms_calls: 1, // Decrypt
            };

            Ok((plaintext, metrics))
        }
        Err(e) => Err(map_kms_error(e)),
    }
}

// ========== SYNC WRAPPERS ==========

/// Sync encrypt - returns (ciphertext, metrics).
pub fn sync_encrypt(
    client: &Client,
    runtime: &Arc<Runtime>,
    key_id: &str,
    context: &HashMap<String, String>,
    plaintext: &str,
) -> PyResult<(String, KmsMetrics)> {
    runtime.block_on(execute_encrypt(
        client.clone(),
        key_id.to_string(),
        context.clone(),
        plaintext.to_string(),
    ))
}

/// Sync decrypt - returns (plaintext, metrics).
pub fn sync_decrypt(
    client: &Client,
    runtime: &Arc<Runtime>,
    context: &HashMap<String, String>,
    ciphertext: &str,
) -> PyResult<(String, KmsMetrics)> {
    runtime.block_on(execute_decrypt(
        client.clone(),
        context.clone(),
        ciphertext.to_string(),
    ))
}

// ========== ASYNC WRAPPERS ==========

/// Async encrypt - returns EncryptResult with ciphertext and metrics.
pub fn async_encrypt<'py>(
    py: Python<'py>,
    client: Client,
    key_id: String,
    context: HashMap<String, String>,
    plaintext: String,
) -> PyResult<Bound<'py, PyAny>> {
    pyo3_async_runtimes::tokio::future_into_py(py, async move {
        let (ciphertext, metrics) = execute_encrypt(client, key_id, context, plaintext).await?;
        Ok(EncryptResult {
            ciphertext,
            metrics,
        })
    })
}

/// Async decrypt - returns DecryptResult with plaintext and metrics.
pub fn async_decrypt<'py>(
    py: Python<'py>,
    client: Client,
    context: HashMap<String, String>,
    ciphertext: String,
) -> PyResult<Bound<'py, PyAny>> {
    pyo3_async_runtimes::tokio::future_into_py(py, async move {
        let (plaintext, metrics) = execute_decrypt(client, context, ciphertext).await?;
        Ok(DecryptResult { plaintext, metrics })
    })
}
