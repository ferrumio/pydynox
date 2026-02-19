//! KMS client that uses shared config from DynamoDBClient.
//!
//! Uses envelope encryption pattern:
//! 1. GenerateDataKey gets a plaintext + encrypted data key
//! 2. Plaintext key encrypts data locally with AES-256-GCM
//! 3. Encrypted key is stored alongside the encrypted data

use crate::client_internal::{AwsConfig, build_kms_client};
use crate::errors::EncryptionException;
use crate::kms::ENCRYPTED_PREFIX;
use crate::kms::operations::{
    DecryptResult, EncryptResult, decrypt_impl, encrypt_impl, sync_decrypt_impl, sync_encrypt_impl,
};
use aws_sdk_kms::Client;
use once_cell::sync::Lazy;
use pyo3::prelude::*;
use std::collections::HashMap;
use std::sync::Arc;
use tokio::runtime::Runtime;

/// Global shared Tokio runtime (same as DynamoDBClient).
static RUNTIME: Lazy<Arc<Runtime>> =
    Lazy::new(|| Arc::new(Runtime::new().expect("Failed to create global Tokio runtime")));

/// KMS encryptor using envelope encryption.
///
/// Uses GenerateDataKey + local AES-256-GCM instead of direct KMS Encrypt.
/// This removes the 4KB size limit and reduces KMS API calls.
#[pyclass]
pub struct KmsEncryptor {
    client: Client,
    runtime: Arc<Runtime>,
    key_id: String,
    context: HashMap<String, String>,
}

#[pymethods]
impl KmsEncryptor {
    /// Create a new KMS encryptor with the same config options as DynamoDBClient.
    #[new]
    #[pyo3(signature = (
        key_id,
        region=None,
        context=None,
        access_key=None,
        secret_key=None,
        session_token=None,
        profile=None,
        role_arn=None,
        role_session_name=None,
        external_id=None,
        endpoint_url=None,
        connect_timeout=None,
        read_timeout=None,
        max_retries=None,
        proxy_url=None
    ))]
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        key_id: String,
        region: Option<String>,
        context: Option<HashMap<String, String>>,
        access_key: Option<String>,
        secret_key: Option<String>,
        session_token: Option<String>,
        profile: Option<String>,
        role_arn: Option<String>,
        role_session_name: Option<String>,
        external_id: Option<String>,
        endpoint_url: Option<String>,
        connect_timeout: Option<f64>,
        read_timeout: Option<f64>,
        max_retries: Option<u32>,
        proxy_url: Option<String>,
    ) -> PyResult<Self> {
        // Set proxy env var if provided
        if let Some(ref proxy) = proxy_url {
            // SAFETY: called during client construction, before any async work starts
            unsafe { std::env::set_var("HTTPS_PROXY", proxy) };
        }

        let config = AwsConfig {
            region,
            access_key,
            secret_key,
            session_token,
            profile,
            role_arn,
            role_session_name,
            external_id,
            endpoint_url,
            connect_timeout,
            read_timeout,
            max_retries,
            proxy_url,
        };

        let runtime = RUNTIME.clone();
        let client = runtime
            .block_on(build_kms_client(&config, None))
            .map_err(|e| {
                EncryptionException::new_err(format!("Failed to create KMS client: {}", e))
            })?;

        Ok(Self {
            client,
            runtime,
            key_id,
            context: context.unwrap_or_default(),
        })
    }

    // ========== ASYNC METHODS (default) ==========

    /// Encrypt a plaintext string (async).
    ///
    /// Returns an awaitable that resolves to EncryptResult.
    pub fn encrypt<'py>(&self, py: Python<'py>, plaintext: &str) -> PyResult<Bound<'py, PyAny>> {
        encrypt_impl(
            py,
            self.client.clone(),
            self.key_id.clone(),
            self.context.clone(),
            plaintext.to_string(),
        )
    }

    /// Encrypt with metrics (async).
    ///
    /// Returns an awaitable that resolves to EncryptResult.
    pub fn encrypt_with_metrics<'py>(
        &self,
        py: Python<'py>,
        plaintext: &str,
    ) -> PyResult<Bound<'py, PyAny>> {
        encrypt_impl(
            py,
            self.client.clone(),
            self.key_id.clone(),
            self.context.clone(),
            plaintext.to_string(),
        )
    }

    /// Decrypt a ciphertext string (async).
    ///
    /// Returns an awaitable that resolves to DecryptResult.
    pub fn decrypt<'py>(&self, py: Python<'py>, ciphertext: &str) -> PyResult<Bound<'py, PyAny>> {
        decrypt_impl(
            py,
            self.client.clone(),
            self.context.clone(),
            ciphertext.to_string(),
        )
    }

    /// Decrypt with metrics (async).
    ///
    /// Returns an awaitable that resolves to DecryptResult.
    pub fn decrypt_with_metrics<'py>(
        &self,
        py: Python<'py>,
        ciphertext: &str,
    ) -> PyResult<Bound<'py, PyAny>> {
        decrypt_impl(
            py,
            self.client.clone(),
            self.context.clone(),
            ciphertext.to_string(),
        )
    }

    // ========== SYNC METHODS ==========

    /// Encrypt a plaintext string (sync).
    pub fn sync_encrypt(&self, py: Python<'_>, plaintext: &str) -> PyResult<String> {
        let (ciphertext, _metrics) = sync_encrypt_impl(
            py,
            &self.client,
            &self.runtime,
            &self.key_id,
            &self.context,
            plaintext,
        )?;
        Ok(ciphertext)
    }

    /// Encrypt with metrics (sync).
    pub fn sync_encrypt_with_metrics(
        &self,
        py: Python<'_>,
        plaintext: &str,
    ) -> PyResult<EncryptResult> {
        let (ciphertext, metrics) = sync_encrypt_impl(
            py,
            &self.client,
            &self.runtime,
            &self.key_id,
            &self.context,
            plaintext,
        )?;
        Ok(EncryptResult {
            ciphertext,
            metrics,
        })
    }

    /// Decrypt a ciphertext string (sync).
    pub fn sync_decrypt(&self, py: Python<'_>, ciphertext: &str) -> PyResult<String> {
        let (plaintext, _metrics) =
            sync_decrypt_impl(py, &self.client, &self.runtime, &self.context, ciphertext)?;
        Ok(plaintext)
    }

    /// Decrypt with metrics (sync).
    pub fn sync_decrypt_with_metrics(
        &self,
        py: Python<'_>,
        ciphertext: &str,
    ) -> PyResult<DecryptResult> {
        let (plaintext, metrics) =
            sync_decrypt_impl(py, &self.client, &self.runtime, &self.context, ciphertext)?;
        Ok(DecryptResult { plaintext, metrics })
    }

    // ========== UTILITY METHODS ==========

    /// Check if a value is encrypted.
    #[staticmethod]
    pub fn is_encrypted(value: &str) -> bool {
        value.starts_with(ENCRYPTED_PREFIX)
    }

    /// Get the KMS key ID.
    #[getter]
    pub fn key_id(&self) -> &str {
        &self.key_id
    }
}
