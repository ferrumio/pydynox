//! KMS client for envelope encryption.
//!
//! Uses GenerateDataKey + local AES instead of direct KMS Encrypt/Decrypt.
//! This removes the 4KB limit and reduces KMS API calls.

use crate::client_internal::{build_credential_provider, ClientConfig, CredentialProvider};
use crate::errors::EncryptionError;
use crate::kms::operations::{async_decrypt, async_encrypt, sync_decrypt, sync_encrypt};
use crate::kms::ENCRYPTED_PREFIX;
use aws_config::meta::region::RegionProviderChain;
use aws_config::retry::RetryConfig;
use aws_config::timeout::TimeoutConfig;
use aws_config::BehaviorVersion;
use aws_sdk_kms::Client;
use pyo3::prelude::*;
use std::collections::HashMap;
use std::sync::Arc;
use std::time::Duration;
use tokio::runtime::Runtime;

/// KMS encryptor using envelope encryption.
///
/// Uses GenerateDataKey + local AES-256-GCM instead of direct KMS Encrypt.
/// This removes the 4KB size limit and reduces KMS API calls.
///
/// Inherits all config from DynamoDB client, only allows region override.
#[pyclass]
pub struct KmsEncryptor {
    client: Client,
    runtime: Arc<Runtime>,
    key_id: String,
    context: HashMap<String, String>,
}

#[pymethods]
impl KmsEncryptor {
    /// Create a new KMS encryptor.
    ///
    /// All parameters except key_id and context are inherited from DynamoDB client.
    /// Only region can be overridden (KMS key may be in different region).
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

        let config = ClientConfig {
            region,
            access_key,
            secret_key,
            session_token,
            profile,
            role_arn,
            role_session_name,
            external_id,
            endpoint_url: endpoint_url.clone(),
            connect_timeout,
            read_timeout,
            max_retries,
            proxy_url,
        };

        let runtime =
            Arc::new(Runtime::new().map_err(|e| {
                EncryptionError::new_err(format!("Failed to create runtime: {}", e))
            })?);

        // Use endpoint_url from config or AWS_ENDPOINT_URL env var
        let effective_endpoint = endpoint_url.or_else(|| {
            std::env::var("AWS_ENDPOINT_URL_KMS")
                .or_else(|_| std::env::var("AWS_ENDPOINT_URL"))
                .ok()
        });

        let client = runtime.block_on(build_kms_client(config, effective_endpoint))?;

        Ok(Self {
            client,
            runtime,
            key_id,
            context: context.unwrap_or_default(),
        })
    }

    // ========== SYNC METHODS ==========

    /// Encrypt a plaintext string using envelope encryption.
    ///
    /// 1. Calls KMS GenerateDataKey once
    /// 2. Encrypts data locally with AES-256-GCM
    /// 3. Returns base64-encoded envelope with "ENC:" prefix
    ///
    /// The envelope contains the encrypted data key + encrypted data.
    pub fn encrypt(&self, plaintext: &str) -> PyResult<String> {
        sync_encrypt(
            &self.client,
            &self.runtime,
            &self.key_id,
            &self.context,
            plaintext,
        )
    }

    /// Decrypt a ciphertext string using envelope encryption.
    ///
    /// 1. Unpacks the envelope to get encrypted DEK + encrypted data
    /// 2. Calls KMS Decrypt to get plaintext DEK
    /// 3. Decrypts data locally with AES-256-GCM
    ///
    /// Expects base64-encoded envelope with "ENC:" prefix.
    pub fn decrypt(&self, ciphertext: &str) -> PyResult<String> {
        sync_decrypt(&self.client, &self.runtime, &self.context, ciphertext)
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

/// Build KMS client from config.
async fn build_kms_client(config: ClientConfig, endpoint_url: Option<String>) -> PyResult<Client> {
    let region_provider =
        RegionProviderChain::first_try(config.region.clone().map(aws_sdk_kms::config::Region::new))
            .or_default_provider()
            .or_else("us-east-1");

    let mut config_loader = aws_config::defaults(BehaviorVersion::latest()).region(region_provider);

    // Configure timeouts
    if config.connect_timeout.is_some() || config.read_timeout.is_some() {
        let mut timeout_builder = TimeoutConfig::builder();
        if let Some(ct) = config.connect_timeout {
            timeout_builder = timeout_builder.connect_timeout(Duration::from_secs_f64(ct));
        }
        if let Some(rt) = config.read_timeout {
            timeout_builder = timeout_builder.read_timeout(Duration::from_secs_f64(rt));
        }
        config_loader = config_loader.timeout_config(timeout_builder.build());
    }

    // Configure retries
    if let Some(retries) = config.max_retries {
        let retry_config = RetryConfig::standard().with_max_attempts(retries);
        config_loader = config_loader.retry_config(retry_config);
    }

    // Configure credentials
    let cred_provider = build_credential_provider(&config).await;
    match cred_provider {
        CredentialProvider::Static(creds) => {
            config_loader = config_loader.credentials_provider(creds);
        }
        CredentialProvider::Profile(provider) => {
            config_loader = config_loader.credentials_provider(provider);
        }
        CredentialProvider::AssumeRole(provider) => {
            config_loader = config_loader.credentials_provider(*provider);
        }
        CredentialProvider::Default => {}
    }

    let sdk_config = config_loader.load().await;
    let mut kms_config = aws_sdk_kms::config::Builder::from(&sdk_config);

    // Configure endpoint override (for localstack)
    if let Some(url) = endpoint_url {
        kms_config = kms_config.endpoint_url(url);
    }

    Ok(Client::from_conf(kms_config.build()))
}
