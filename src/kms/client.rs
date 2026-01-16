//! KMS client that uses shared config from DynamoDBClient.
//!
//! Uses envelope encryption pattern:
//! 1. GenerateDataKey gets a plaintext + encrypted data key
//! 2. Plaintext key encrypts data locally with AES-256-GCM
//! 3. Encrypted key is stored alongside the encrypted data

use crate::client_internal::{build_kms_client, AwsConfig};
use crate::errors::EncryptionException;
use crate::kms::operations::{
    async_decrypt, async_encrypt, sync_decrypt, sync_encrypt, DecryptResult, EncryptResult,
};
use crate::kms::ENCRYPTED_PREFIX;
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
            std::env::set_var("HTTPS_PROXY", proxy);
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

    // ========== SYNC METHODS ==========

    /// Encrypt a plaintext string using envelope encryption.
    pub fn encrypt(&self, plaintext: &str) -> PyResult<String> {
        let (ciphertext, _metrics) = sync_encrypt(
            &self.client,
            &self.runtime,
            &self.key_id,
            &self.context,
            plaintext,
        )?;
        Ok(ciphertext)
    }

    /// Encrypt with metrics.
    pub fn encrypt_with_metrics(&self, plaintext: &str) -> PyResult<EncryptResult> {
        let (ciphertext, metrics) = sync_encrypt(
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

    /// Decrypt a ciphertext string using envelope encryption.
    pub fn decrypt(&self, ciphertext: &str) -> PyResult<String> {
        let (plaintext, _metrics) =
            sync_decrypt(&self.client, &self.runtime, &self.context, ciphertext)?;
        Ok(plaintext)
    }

    /// Decrypt with metrics.
    pub fn decrypt_with_metrics(&self, ciphertext: &str) -> PyResult<DecryptResult> {
        let (plaintext, metrics) =
            sync_decrypt(&self.client, &self.runtime, &self.context, ciphertext)?;
        Ok(DecryptResult { plaintext, metrics })
    }

    // ========== ASYNC METHODS ==========

    /// Async encrypt a plaintext string.
    pub fn async_encrypt<'py>(
        &self,
        py: Python<'py>,
        plaintext: &str,
    ) -> PyResult<Bound<'py, PyAny>> {
        async_encrypt(
            py,
            self.client.clone(),
            self.key_id.clone(),
            self.context.clone(),
            plaintext.to_string(),
        )
    }

    /// Async decrypt a ciphertext string.
    pub fn async_decrypt<'py>(
        &self,
        py: Python<'py>,
        ciphertext: &str,
    ) -> PyResult<Bound<'py, PyAny>> {
        async_decrypt(
            py,
            self.client.clone(),
            self.context.clone(),
            ciphertext.to_string(),
        )
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
