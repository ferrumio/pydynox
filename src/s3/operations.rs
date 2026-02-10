//! S3 operations - upload, download, presigned URLs, delete.

use crate::errors::{map_s3_error, S3Exception};
use aws_sdk_s3::presigning::PresigningConfig;
use aws_sdk_s3::primitives::ByteStream;
use aws_sdk_s3::Client;
use pyo3::prelude::*;
use pyo3::types::{PyBytes, PyDict};
use std::collections::HashMap;
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::runtime::Runtime;

/// Threshold for using multipart upload (10MB).
const MULTIPART_THRESHOLD: usize = 10 * 1024 * 1024;

/// Minimum part size for multipart upload (5MB).
const MIN_PART_SIZE: usize = 5 * 1024 * 1024;

/// Default part size for multipart upload (10MB).
const DEFAULT_PART_SIZE: usize = 10 * 1024 * 1024;

/// Metrics from an S3 operation.
#[pyclass(from_py_object)]
#[derive(Clone, Debug, Default)]
pub struct S3Metrics {
    #[pyo3(get)]
    pub duration_ms: f64,
    #[pyo3(get)]
    pub calls: u32,
    #[pyo3(get)]
    pub bytes_uploaded: u64,
    #[pyo3(get)]
    pub bytes_downloaded: u64,
}

#[pymethods]
impl S3Metrics {
    #[new]
    #[pyo3(signature = (duration_ms=0.0, calls=0, bytes_uploaded=0, bytes_downloaded=0))]
    pub fn new(duration_ms: f64, calls: u32, bytes_uploaded: u64, bytes_downloaded: u64) -> Self {
        Self {
            duration_ms,
            calls,
            bytes_uploaded,
            bytes_downloaded,
        }
    }

    fn __repr__(&self) -> String {
        format!(
            "S3Metrics(duration_ms={:.2}, calls={}, bytes_uploaded={}, bytes_downloaded={})",
            self.duration_ms, self.calls, self.bytes_uploaded, self.bytes_downloaded
        )
    }
}

/// S3 file metadata returned after upload.
#[pyclass(from_py_object)]
#[derive(Clone)]
pub struct S3Metadata {
    #[pyo3(get)]
    pub bucket: String,
    #[pyo3(get)]
    pub key: String,
    #[pyo3(get)]
    pub size: u64,
    #[pyo3(get)]
    pub etag: String,
    #[pyo3(get)]
    pub content_type: Option<String>,
    #[pyo3(get)]
    pub last_modified: Option<String>,
    #[pyo3(get)]
    pub version_id: Option<String>,
    #[pyo3(get)]
    pub metadata: Option<HashMap<String, String>>,
}

#[pymethods]
impl S3Metadata {
    fn __repr__(&self) -> String {
        format!(
            "S3Metadata(bucket='{}', key='{}', size={}, etag='{}')",
            self.bucket, self.key, self.size, self.etag
        )
    }

    fn to_dict<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyDict>> {
        let dict = PyDict::new(py);
        dict.set_item("bucket", &self.bucket)?;
        dict.set_item("key", &self.key)?;
        dict.set_item("size", self.size)?;
        dict.set_item("etag", &self.etag)?;
        if let Some(ct) = &self.content_type {
            dict.set_item("content_type", ct)?;
        }
        if let Some(lm) = &self.last_modified {
            dict.set_item("last_modified", lm)?;
        }
        if let Some(vid) = &self.version_id {
            dict.set_item("version_id", vid)?;
        }
        if let Some(meta) = &self.metadata {
            dict.set_item("metadata", meta.clone())?;
        }
        Ok(dict)
    }
}

// ========== RESULT TYPES ==========

pub struct UploadResult {
    pub metadata: S3Metadata,
    pub metrics: S3Metrics,
}

pub struct DownloadResult {
    pub data: Vec<u8>,
    pub metrics: S3Metrics,
}

pub struct SaveToFileResult {
    pub bytes_written: u64,
    pub metrics: S3Metrics,
}

pub struct DeleteResult {
    pub metrics: S3Metrics,
}

pub struct PresignedUrlResult {
    pub url: String,
    pub metrics: S3Metrics,
}

pub struct HeadResult {
    pub metadata: S3Metadata,
    pub metrics: S3Metrics,
}

// ========== CORE ASYNC OPERATIONS (execute_*) ==========

/// Core async upload operation.
pub async fn execute_upload(
    client: Client,
    bucket: String,
    key: String,
    data: Vec<u8>,
    content_type: Option<String>,
    metadata: Option<HashMap<String, String>>,
) -> Result<UploadResult, String> {
    let start = Instant::now();
    let size = data.len();

    let (result, calls) = if size > MULTIPART_THRESHOLD {
        execute_multipart_upload(
            client,
            &bucket,
            &key,
            data,
            content_type.clone(),
            metadata.clone(),
        )
        .await?
    } else {
        let meta = execute_simple_upload(
            client,
            &bucket,
            &key,
            data,
            content_type.clone(),
            metadata.clone(),
        )
        .await?;
        (meta, 1u32)
    };

    let duration_ms = start.elapsed().as_secs_f64() * 1000.0;

    Ok(UploadResult {
        metadata: result,
        metrics: S3Metrics {
            duration_ms,
            calls,
            bytes_uploaded: size as u64,
            bytes_downloaded: 0,
        },
    })
}

async fn execute_simple_upload(
    client: Client,
    bucket: &str,
    key: &str,
    data: Vec<u8>,
    content_type: Option<String>,
    metadata: Option<HashMap<String, String>>,
) -> Result<S3Metadata, String> {
    let size = data.len() as u64;

    let mut req = client
        .put_object()
        .bucket(bucket)
        .key(key)
        .body(ByteStream::from(data));

    if let Some(ct) = &content_type {
        req = req.content_type(ct);
    }

    if let Some(meta) = &metadata {
        for (k, v) in meta {
            req = req.metadata(k, v);
        }
    }

    let resp = req.send().await.map_err(|e| {
        let py_err = map_s3_error(e, Some(bucket), Some(key));
        format!("{}", py_err)
    })?;

    Ok(S3Metadata {
        bucket: bucket.to_string(),
        key: key.to_string(),
        size,
        etag: resp.e_tag().unwrap_or("").trim_matches('"').to_string(),
        content_type,
        last_modified: None,
        version_id: resp.version_id().map(|s| s.to_string()),
        metadata,
    })
}

async fn execute_multipart_upload(
    client: Client,
    bucket: &str,
    key: &str,
    data: Vec<u8>,
    content_type: Option<String>,
    metadata: Option<HashMap<String, String>>,
) -> Result<(S3Metadata, u32), String> {
    let size = data.len() as u64;

    let mut create_req = client.create_multipart_upload().bucket(bucket).key(key);

    if let Some(ct) = &content_type {
        create_req = create_req.content_type(ct);
    }

    if let Some(meta) = &metadata {
        for (k, v) in meta {
            create_req = create_req.metadata(k, v);
        }
    }

    let create_resp = create_req.send().await.map_err(|e| {
        let py_err = map_s3_error(e, Some(bucket), Some(key));
        format!("{}", py_err)
    })?;

    let upload_id = create_resp
        .upload_id()
        .ok_or("No upload ID returned")?
        .to_string();

    let part_size = calculate_part_size(data.len());
    let mut parts = Vec::new();
    let mut part_number = 1;
    let mut api_calls: u32 = 1;

    for chunk in data.chunks(part_size) {
        let upload_result = client
            .upload_part()
            .bucket(bucket)
            .key(key)
            .upload_id(&upload_id)
            .part_number(part_number)
            .body(ByteStream::from(chunk.to_vec()))
            .send()
            .await;

        api_calls += 1;

        match upload_result {
            Ok(resp) => {
                parts.push(
                    aws_sdk_s3::types::CompletedPart::builder()
                        .part_number(part_number)
                        .e_tag(resp.e_tag().unwrap_or(""))
                        .build(),
                );
            }
            Err(e) => {
                let _ = client
                    .abort_multipart_upload()
                    .bucket(bucket)
                    .key(key)
                    .upload_id(&upload_id)
                    .send()
                    .await;
                let py_err = map_s3_error(e, Some(bucket), Some(key));
                return Err(format!("Failed to upload part {}: {}", part_number, py_err));
            }
        }

        part_number += 1;
    }

    let completed = aws_sdk_s3::types::CompletedMultipartUpload::builder()
        .set_parts(Some(parts))
        .build();

    let complete_resp = client
        .complete_multipart_upload()
        .bucket(bucket)
        .key(key)
        .upload_id(&upload_id)
        .multipart_upload(completed)
        .send()
        .await
        .map_err(|e| {
            let py_err = map_s3_error(e, Some(bucket), Some(key));
            format!("{}", py_err)
        })?;

    api_calls += 1;

    Ok((
        S3Metadata {
            bucket: bucket.to_string(),
            key: key.to_string(),
            size,
            etag: complete_resp
                .e_tag()
                .unwrap_or("")
                .trim_matches('"')
                .to_string(),
            content_type,
            last_modified: None,
            version_id: complete_resp.version_id().map(|s| s.to_string()),
            metadata,
        },
        api_calls,
    ))
}

pub async fn execute_download(
    client: Client,
    bucket: String,
    key: String,
) -> Result<DownloadResult, String> {
    let start = Instant::now();

    let resp = client
        .get_object()
        .bucket(&bucket)
        .key(&key)
        .send()
        .await
        .map_err(|e| {
            let py_err = map_s3_error(e, Some(&bucket), Some(&key));
            format!("{}", py_err)
        })?;

    let data = resp
        .body
        .collect()
        .await
        .map_err(|e| format!("Failed to read S3 body: {}", e))
        .map(|data| data.into_bytes().to_vec())?;

    let duration_ms = start.elapsed().as_secs_f64() * 1000.0;
    let bytes_downloaded = data.len() as u64;

    Ok(DownloadResult {
        data,
        metrics: S3Metrics {
            duration_ms,
            calls: 1,
            bytes_uploaded: 0,
            bytes_downloaded,
        },
    })
}

pub async fn execute_save_to_file(
    client: Client,
    bucket: String,
    key: String,
    path: String,
) -> Result<SaveToFileResult, String> {
    use tokio::io::AsyncWriteExt;

    let start = Instant::now();

    let resp = client
        .get_object()
        .bucket(&bucket)
        .key(&key)
        .send()
        .await
        .map_err(|e| {
            let py_err = map_s3_error(e, Some(&bucket), Some(&key));
            format!("{}", py_err)
        })?;

    let mut file = tokio::fs::File::create(&path)
        .await
        .map_err(|e| format!("Failed to create file: {}", e))?;

    let mut stream = resp.body;
    let mut total_bytes: u64 = 0;

    while let Some(chunk) = stream
        .try_next()
        .await
        .map_err(|e| format!("Failed to read chunk: {}", e))?
    {
        total_bytes += chunk.len() as u64;
        file.write_all(&chunk)
            .await
            .map_err(|e| format!("Failed to write to file: {}", e))?;
    }

    file.flush()
        .await
        .map_err(|e| format!("Failed to flush file: {}", e))?;

    let duration_ms = start.elapsed().as_secs_f64() * 1000.0;

    Ok(SaveToFileResult {
        bytes_written: total_bytes,
        metrics: S3Metrics {
            duration_ms,
            calls: 1,
            bytes_uploaded: 0,
            bytes_downloaded: total_bytes,
        },
    })
}

pub async fn execute_presigned_url(
    client: Client,
    bucket: String,
    key: String,
    expires_secs: u64,
) -> Result<PresignedUrlResult, String> {
    let start = Instant::now();

    let presign_config = PresigningConfig::expires_in(Duration::from_secs(expires_secs))
        .map_err(|e| format!("Invalid expiration: {}", e))?;

    let presigned = client
        .get_object()
        .bucket(&bucket)
        .key(&key)
        .presigned(presign_config)
        .await
        .map_err(|e| format!("Failed to generate presigned URL: {}", e))?;

    let duration_ms = start.elapsed().as_secs_f64() * 1000.0;

    Ok(PresignedUrlResult {
        url: presigned.uri().to_string(),
        metrics: S3Metrics {
            duration_ms,
            calls: 0,
            bytes_uploaded: 0,
            bytes_downloaded: 0,
        },
    })
}

pub async fn execute_delete(
    client: Client,
    bucket: String,
    key: String,
) -> Result<DeleteResult, String> {
    let start = Instant::now();

    client
        .delete_object()
        .bucket(&bucket)
        .key(&key)
        .send()
        .await
        .map_err(|e| {
            let py_err = map_s3_error(e, Some(&bucket), Some(&key));
            format!("{}", py_err)
        })?;

    let duration_ms = start.elapsed().as_secs_f64() * 1000.0;

    Ok(DeleteResult {
        metrics: S3Metrics {
            duration_ms,
            calls: 1,
            bytes_uploaded: 0,
            bytes_downloaded: 0,
        },
    })
}

pub async fn execute_head(
    client: Client,
    bucket: String,
    key: String,
) -> Result<HeadResult, String> {
    let start = Instant::now();

    let resp = client
        .head_object()
        .bucket(&bucket)
        .key(&key)
        .send()
        .await
        .map_err(|e| {
            let py_err = map_s3_error(e, Some(&bucket), Some(&key));
            format!("{}", py_err)
        })?;

    let duration_ms = start.elapsed().as_secs_f64() * 1000.0;

    let last_modified = resp.last_modified().map(|dt| dt.to_string());
    let metadata = resp.metadata().map(|m| {
        m.iter()
            .map(|(k, v)| (k.clone(), v.clone()))
            .collect::<HashMap<String, String>>()
    });

    Ok(HeadResult {
        metadata: S3Metadata {
            bucket,
            key,
            size: resp.content_length().unwrap_or(0) as u64,
            etag: resp.e_tag().unwrap_or("").trim_matches('"').to_string(),
            content_type: resp.content_type().map(|s| s.to_string()),
            last_modified,
            version_id: resp.version_id().map(|s| s.to_string()),
            metadata,
        },
        metrics: S3Metrics {
            duration_ms,
            calls: 1,
            bytes_uploaded: 0,
            bytes_downloaded: 0,
        },
    })
}

// ========== HELPER FUNCTIONS ==========

/// Calculate optimal part size for multipart upload.
pub fn calculate_part_size(total_size: usize) -> usize {
    if total_size <= MULTIPART_THRESHOLD {
        return total_size;
    }

    // Target ~100 parts for large files
    let target_parts = 100;
    let calculated = total_size / target_parts;

    if calculated < MIN_PART_SIZE {
        MIN_PART_SIZE
    } else if calculated > DEFAULT_PART_SIZE * 10 {
        DEFAULT_PART_SIZE * 10
    } else {
        calculated
    }
}

// ========== ASYNC WRAPPERS (no prefix) - return Python awaitable ==========

/// Async upload bytes - returns Python awaitable.
#[allow(clippy::too_many_arguments)]
pub fn upload_bytes<'py>(
    py: Python<'py>,
    client: Client,
    bucket: String,
    key: String,
    data: &Bound<'_, PyBytes>,
    content_type: Option<String>,
    metadata: Option<HashMap<String, String>>,
) -> PyResult<Bound<'py, PyAny>> {
    let data_vec = data.as_bytes().to_vec();

    pyo3_async_runtimes::tokio::future_into_py(py, async move {
        let result = execute_upload(client, bucket, key, data_vec, content_type, metadata)
            .await
            .map_err(S3Exception::new_err)?;
        Ok((result.metadata, result.metrics))
    })
}

/// Async download bytes - returns Python awaitable.
pub fn download_bytes(
    py: Python<'_>,
    client: Client,
    bucket: String,
    key: String,
) -> PyResult<Bound<'_, PyAny>> {
    pyo3_async_runtimes::tokio::future_into_py(py, async move {
        let result = execute_download(client, bucket, key)
            .await
            .map_err(S3Exception::new_err)?;
        Python::attach(|py| {
            let bytes = PyBytes::new(py, &result.data);
            Ok((bytes.unbind(), result.metrics))
        })
    })
}

/// Async presigned URL - returns Python awaitable.
pub fn presigned_url(
    py: Python<'_>,
    client: Client,
    bucket: String,
    key: String,
    expires_secs: u64,
) -> PyResult<Bound<'_, PyAny>> {
    pyo3_async_runtimes::tokio::future_into_py(py, async move {
        let result = execute_presigned_url(client, bucket, key, expires_secs)
            .await
            .map_err(S3Exception::new_err)?;
        Ok((result.url, result.metrics))
    })
}

/// Async delete object - returns Python awaitable.
pub fn delete_object(
    py: Python<'_>,
    client: Client,
    bucket: String,
    key: String,
) -> PyResult<Bound<'_, PyAny>> {
    pyo3_async_runtimes::tokio::future_into_py(py, async move {
        let result = execute_delete(client, bucket, key)
            .await
            .map_err(S3Exception::new_err)?;
        Ok(result.metrics)
    })
}

/// Async head object - returns Python awaitable.
pub fn head_object(
    py: Python<'_>,
    client: Client,
    bucket: String,
    key: String,
) -> PyResult<Bound<'_, PyAny>> {
    pyo3_async_runtimes::tokio::future_into_py(py, async move {
        let result = execute_head(client, bucket, key)
            .await
            .map_err(S3Exception::new_err)?;
        Ok((result.metadata, result.metrics))
    })
}

/// Async save to file - returns Python awaitable.
pub fn save_to_file(
    py: Python<'_>,
    client: Client,
    bucket: String,
    key: String,
    path: String,
) -> PyResult<Bound<'_, PyAny>> {
    pyo3_async_runtimes::tokio::future_into_py(py, async move {
        let result = execute_save_to_file(client, bucket, key, path)
            .await
            .map_err(S3Exception::new_err)?;
        Ok((result.bytes_written, result.metrics))
    })
}

// ========== SYNC WRAPPERS (sync_ prefix) - block until complete ==========

/// Sync upload bytes - blocks until complete.
#[allow(clippy::too_many_arguments)]
pub fn sync_upload_bytes(
    py: Python<'_>,
    client: &Client,
    runtime: &Arc<Runtime>,
    bucket: &str,
    key: &str,
    data: &Bound<'_, PyBytes>,
    content_type: Option<String>,
    metadata: Option<HashMap<String, String>>,
) -> PyResult<(S3Metadata, S3Metrics)> {
    let data_vec = data.as_bytes().to_vec();
    let client = client.clone();
    let bucket = bucket.to_string();
    let key = key.to_string();

    py.detach(|| {
        runtime.block_on(async {
            let result = execute_upload(client, bucket, key, data_vec, content_type, metadata)
                .await
                .map_err(S3Exception::new_err)?;
            Ok((result.metadata, result.metrics))
        })
    })
}

/// Sync download bytes - blocks until complete.
pub fn sync_download_bytes<'py>(
    py: Python<'py>,
    client: &Client,
    runtime: &Arc<Runtime>,
    bucket: &str,
    key: &str,
) -> PyResult<(Bound<'py, PyBytes>, S3Metrics)> {
    let client = client.clone();
    let bucket = bucket.to_string();
    let key = key.to_string();

    let result = py.detach(|| {
        runtime.block_on(async {
            execute_download(client, bucket, key)
                .await
                .map_err(S3Exception::new_err)
        })
    })?;

    let bytes = PyBytes::new(py, &result.data);
    Ok((bytes, result.metrics))
}

/// Sync presigned URL - blocks until complete.
pub fn sync_presigned_url(
    client: &Client,
    runtime: &Arc<Runtime>,
    bucket: &str,
    key: &str,
    expires_secs: u64,
) -> PyResult<(String, S3Metrics)> {
    let client = client.clone();
    let bucket = bucket.to_string();
    let key = key.to_string();

    runtime.block_on(async {
        let result = execute_presigned_url(client, bucket, key, expires_secs)
            .await
            .map_err(S3Exception::new_err)?;
        Ok((result.url, result.metrics))
    })
}

/// Sync delete object - blocks until complete.
pub fn sync_delete_object(
    client: &Client,
    runtime: &Arc<Runtime>,
    bucket: &str,
    key: &str,
) -> PyResult<S3Metrics> {
    let client = client.clone();
    let bucket = bucket.to_string();
    let key = key.to_string();

    runtime.block_on(async {
        let result = execute_delete(client, bucket, key)
            .await
            .map_err(S3Exception::new_err)?;
        Ok(result.metrics)
    })
}

/// Sync head object - blocks until complete.
pub fn sync_head_object(
    client: &Client,
    runtime: &Arc<Runtime>,
    bucket: &str,
    key: &str,
) -> PyResult<(S3Metadata, S3Metrics)> {
    let client = client.clone();
    let bucket = bucket.to_string();
    let key = key.to_string();

    runtime.block_on(async {
        let result = execute_head(client, bucket, key)
            .await
            .map_err(S3Exception::new_err)?;
        Ok((result.metadata, result.metrics))
    })
}

/// Sync save to file - blocks until complete.
pub fn sync_save_to_file(
    client: &Client,
    runtime: &Arc<Runtime>,
    bucket: &str,
    key: &str,
    path: &str,
) -> PyResult<(u64, S3Metrics)> {
    let client = client.clone();
    let bucket = bucket.to_string();
    let key = key.to_string();
    let path = path.to_string();

    runtime.block_on(async {
        let result = execute_save_to_file(client, bucket, key, path)
            .await
            .map_err(S3Exception::new_err)?;
        Ok((result.bytes_written, result.metrics))
    })
}
