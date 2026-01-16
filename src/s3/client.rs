//! S3 client that uses shared config from DynamoDBClient.
//!
//! This module provides S3 operations that can be used standalone or
//! through the DynamoDBClient's lazy S3 client.

use crate::client_internal::{build_s3_client, AwsConfig};
use crate::errors::S3Exception;
use crate::s3::operations::{
    async_delete_object, async_download_bytes, async_head_object, async_presigned_url,
    async_save_to_file, async_upload_bytes, delete_object, download_bytes, head_object,
    presigned_url, save_to_file, upload_bytes, S3Metadata, S3Metrics,
};
use aws_sdk_s3::Client;
use once_cell::sync::Lazy;
use pyo3::prelude::*;
use pyo3::types::PyBytes;
use std::sync::Arc;
use tokio::runtime::Runtime;

/// Global shared Tokio runtime (same as DynamoDBClient).
static RUNTIME: Lazy<Arc<Runtime>> =
    Lazy::new(|| Arc::new(Runtime::new().expect("Failed to create global Tokio runtime")));

/// S3 client for standalone use.
///
/// For most cases, use DynamoDBClient.get_s3_client() instead.
/// This class is for cases where you need S3 without DynamoDB.
#[pyclass(name = "S3Operations")]
pub struct S3Client {
    client: Client,
    runtime: Arc<Runtime>,
}

#[pymethods]
impl S3Client {
    /// Create S3Client with the same config options as DynamoDBClient.
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
            .block_on(build_s3_client(&config, None))
            .map_err(|e| S3Exception::new_err(format!("Failed to create S3 client: {}", e)))?;

        Ok(Self { client, runtime })
    }

    // ========== SYNC METHODS ==========

    /// Upload bytes to S3. Returns (S3Metadata, S3Metrics).
    #[pyo3(signature = (bucket, key, data, content_type=None, metadata=None))]
    pub fn upload_bytes(
        &self,
        py: Python<'_>,
        bucket: &str,
        key: &str,
        data: &Bound<'_, PyBytes>,
        content_type: Option<String>,
        metadata: Option<std::collections::HashMap<String, String>>,
    ) -> PyResult<(S3Metadata, S3Metrics)> {
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

    /// Download file from S3 as bytes. Returns (bytes, S3Metrics).
    pub fn download_bytes<'py>(
        &self,
        py: Python<'py>,
        bucket: &str,
        key: &str,
    ) -> PyResult<(Bound<'py, PyBytes>, S3Metrics)> {
        download_bytes(py, &self.client, &self.runtime, bucket, key)
    }

    /// Generate a presigned URL for download. Returns (url, S3Metrics).
    #[pyo3(signature = (bucket, key, expires_secs=3600))]
    pub fn presigned_url(
        &self,
        bucket: &str,
        key: &str,
        expires_secs: u64,
    ) -> PyResult<(String, S3Metrics)> {
        presigned_url(&self.client, &self.runtime, bucket, key, expires_secs)
    }

    /// Delete an object from S3. Returns S3Metrics.
    pub fn delete_object(&self, bucket: &str, key: &str) -> PyResult<S3Metrics> {
        delete_object(&self.client, &self.runtime, bucket, key)
    }

    /// Get object metadata without downloading. Returns (S3Metadata, S3Metrics).
    pub fn head_object(&self, bucket: &str, key: &str) -> PyResult<(S3Metadata, S3Metrics)> {
        head_object(&self.client, &self.runtime, bucket, key)
    }

    // ========== ASYNC METHODS ==========

    /// Async upload bytes to S3. Returns (S3Metadata, S3Metrics).
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

    /// Async download file from S3 as bytes. Returns (bytes, S3Metrics).
    pub fn async_download_bytes<'py>(
        &self,
        py: Python<'py>,
        bucket: &str,
        key: &str,
    ) -> PyResult<Bound<'py, PyAny>> {
        async_download_bytes(py, self.client.clone(), bucket.to_string(), key.to_string())
    }

    /// Async generate a presigned URL for download. Returns (url, S3Metrics).
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

    /// Async delete an object from S3. Returns S3Metrics.
    pub fn async_delete_object<'py>(
        &self,
        py: Python<'py>,
        bucket: &str,
        key: &str,
    ) -> PyResult<Bound<'py, PyAny>> {
        async_delete_object(py, self.client.clone(), bucket.to_string(), key.to_string())
    }

    /// Async get object metadata without downloading. Returns (S3Metadata, S3Metrics).
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
    /// Returns (bytes_written, S3Metrics).
    pub fn save_to_file(&self, bucket: &str, key: &str, path: &str) -> PyResult<(u64, S3Metrics)> {
        save_to_file(&self.client, &self.runtime, bucket, key, path)
    }

    /// Async save S3 object directly to file. Returns (bytes_written, S3Metrics).
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
