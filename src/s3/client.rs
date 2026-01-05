//! S3 client that inherits config from DynamoDB client.

use crate::client_internal::{build_credential_provider, ClientConfig, CredentialProvider};
use crate::errors::S3AttributeError;
use crate::s3::operations::{
    async_delete_object, async_download_bytes, async_head_object, async_presigned_url,
    async_save_to_file, async_upload_bytes, delete_object, download_bytes, head_object,
    presigned_url, save_to_file, upload_bytes, S3Metadata,
};
use aws_config::meta::region::RegionProviderChain;
use aws_config::retry::RetryConfig;
use aws_config::timeout::TimeoutConfig;
use aws_config::BehaviorVersion;
use aws_sdk_s3::Client;
use pyo3::prelude::*;
use pyo3::types::PyBytes;
use std::sync::Arc;
use std::time::Duration;
use tokio::runtime::Runtime;

/// S3 client that inherits all config from DynamoDB client.
///
/// Only region can be overridden (S3 bucket may be in different region).
#[pyclass(name = "S3Operations")]
pub struct S3Client {
    client: Client,
    runtime: Arc<Runtime>,
}

#[pymethods]
impl S3Client {
    /// Create S3Client from DynamoDB client config.
    ///
    /// All parameters are inherited from DynamoDB client config.
    /// Only region can be overridden (S3 bucket may be in different region).
    #[new]
    #[pyo3(signature = (
        region=None,
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
        region: Option<String>,
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
                S3AttributeError::new_err(format!("Failed to create runtime: {}", e))
            })?);

        let client = runtime.block_on(build_s3_client(config, endpoint_url))?;

        Ok(Self { client, runtime })
    }

    // ========== SYNC METHODS ==========

    /// Upload bytes to S3.
    #[pyo3(signature = (bucket, key, data, content_type=None, metadata=None))]
    pub fn upload_bytes(
        &self,
        py: Python<'_>,
        bucket: &str,
        key: &str,
        data: &Bound<'_, PyBytes>,
        content_type: Option<String>,
        metadata: Option<std::collections::HashMap<String, String>>,
    ) -> PyResult<S3Metadata> {
        upload_bytes(
            py,
            &self.client,
            &self.runtime,
            bucket,
            key,
            data,
            content_type,
            metadata,
        )
    }

    /// Download file from S3 as bytes.
    pub fn download_bytes<'py>(
        &self,
        py: Python<'py>,
        bucket: &str,
        key: &str,
    ) -> PyResult<Bound<'py, PyBytes>> {
        download_bytes(py, &self.client, &self.runtime, bucket, key)
    }

    /// Generate a presigned URL for download.
    #[pyo3(signature = (bucket, key, expires_secs=3600))]
    pub fn presigned_url(&self, bucket: &str, key: &str, expires_secs: u64) -> PyResult<String> {
        presigned_url(&self.client, &self.runtime, bucket, key, expires_secs)
    }

    /// Delete an object from S3.
    pub fn delete_object(&self, bucket: &str, key: &str) -> PyResult<()> {
        delete_object(&self.client, &self.runtime, bucket, key)
    }

    /// Get object metadata without downloading.
    pub fn head_object(&self, bucket: &str, key: &str) -> PyResult<S3Metadata> {
        head_object(&self.client, &self.runtime, bucket, key)
    }

    // ========== ASYNC METHODS ==========

    /// Async upload bytes to S3.
    #[pyo3(signature = (bucket, key, data, content_type=None, metadata=None))]
    pub fn async_upload_bytes<'py>(
        &self,
        py: Python<'py>,
        bucket: &str,
        key: &str,
        data: &Bound<'_, PyBytes>,
        content_type: Option<String>,
        metadata: Option<std::collections::HashMap<String, String>>,
    ) -> PyResult<Bound<'py, PyAny>> {
        async_upload_bytes(
            py,
            self.client.clone(),
            bucket.to_string(),
            key.to_string(),
            data,
            content_type,
            metadata,
        )
    }

    /// Async download file from S3 as bytes.
    pub fn async_download_bytes<'py>(
        &self,
        py: Python<'py>,
        bucket: &str,
        key: &str,
    ) -> PyResult<Bound<'py, PyAny>> {
        async_download_bytes(py, self.client.clone(), bucket.to_string(), key.to_string())
    }

    /// Async generate a presigned URL for download.
    #[pyo3(signature = (bucket, key, expires_secs=3600))]
    pub fn async_presigned_url<'py>(
        &self,
        py: Python<'py>,
        bucket: &str,
        key: &str,
        expires_secs: u64,
    ) -> PyResult<Bound<'py, PyAny>> {
        async_presigned_url(
            py,
            self.client.clone(),
            bucket.to_string(),
            key.to_string(),
            expires_secs,
        )
    }

    /// Async delete an object from S3.
    pub fn async_delete_object<'py>(
        &self,
        py: Python<'py>,
        bucket: &str,
        key: &str,
    ) -> PyResult<Bound<'py, PyAny>> {
        async_delete_object(py, self.client.clone(), bucket.to_string(), key.to_string())
    }

    /// Async get object metadata without downloading.
    pub fn async_head_object<'py>(
        &self,
        py: Python<'py>,
        bucket: &str,
        key: &str,
    ) -> PyResult<Bound<'py, PyAny>> {
        async_head_object(py, self.client.clone(), bucket.to_string(), key.to_string())
    }

    // ========== STREAMING METHODS ==========

    /// Save S3 object directly to file (streaming, memory efficient).
    ///
    /// Use this for large files to avoid loading into memory.
    pub fn save_to_file(&self, bucket: &str, key: &str, path: &str) -> PyResult<u64> {
        save_to_file(&self.client, &self.runtime, bucket, key, path)
    }

    /// Async save S3 object directly to file.
    pub fn async_save_to_file<'py>(
        &self,
        py: Python<'py>,
        bucket: &str,
        key: &str,
        path: &str,
    ) -> PyResult<Bound<'py, PyAny>> {
        async_save_to_file(
            py,
            self.client.clone(),
            bucket.to_string(),
            key.to_string(),
            path.to_string(),
        )
    }
}

/// Build S3 client from config.
async fn build_s3_client(config: ClientConfig, endpoint_url: Option<String>) -> PyResult<Client> {
    let region_provider =
        RegionProviderChain::first_try(config.region.clone().map(aws_sdk_s3::config::Region::new))
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
    let mut s3_config = aws_sdk_s3::config::Builder::from(&sdk_config);

    // Configure endpoint override (for localstack)
    if let Some(url) = endpoint_url {
        s3_config = s3_config.endpoint_url(url).force_path_style(true);
    }

    Ok(Client::from_conf(s3_config.build()))
}
