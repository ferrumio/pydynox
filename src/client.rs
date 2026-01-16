//! DynamoDB client module.
//!
//! Provides a flexible DynamoDB client that supports multiple credential sources:
//! - Environment variables
//! - Hardcoded credentials
//! - AWS profiles (including SSO)
//! - AssumeRole (cross-account)
//! - Default chain (instance profile, container, EKS IRSA, GitHub OIDC, etc.)
//!
//! Also supports client configuration:
//! - Connect/read timeouts
//! - Max retries
//! - Proxy
//!
//! The main struct is [`DynamoDBClient`], which wraps the AWS SDK client.
//! S3 and KMS clients are created lazily when needed, sharing the same config.

use aws_sdk_dynamodb::Client;
use aws_sdk_kms::Client as KmsClient;
use aws_sdk_s3::Client as S3Client;
use once_cell::sync::{Lazy, OnceCell};
use pyo3::prelude::*;
use pyo3::types::PyDict;
use std::sync::Arc;
use tokio::runtime::Runtime;

use crate::basic_operations;
use crate::batch_operations;
use crate::client_internal::{build_client, build_kms_client, build_s3_client, AwsConfig};
use crate::metrics::OperationMetrics;
use crate::table_operations;
use crate::transaction_operations;

/// Global shared Tokio runtime.
///
/// Using a single runtime avoids deadlocks on Windows when multiple
/// DynamoDBClient instances are created. Also shared by S3/KMS clients.
static RUNTIME: Lazy<Arc<Runtime>> =
    Lazy::new(|| Arc::new(Runtime::new().expect("Failed to create global Tokio runtime")));

/// DynamoDB client with flexible credential configuration.
///
/// Supports multiple credential sources in order of priority:
/// 1. Hardcoded credentials (access_key, secret_key, session_token)
/// 2. AssumeRole (cross-account access)
/// 3. AWS profile from ~/.aws/credentials (supports SSO)
/// 4. Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
/// 5. Default credential chain (instance profile, container, EKS IRSA, GitHub OIDC, etc.)
///
/// Also supports client configuration:
/// - connect_timeout: Connection timeout in seconds
/// - read_timeout: Read timeout in seconds
/// - max_retries: Maximum number of retries
/// - proxy_url: HTTP/HTTPS proxy
///
/// S3 and KMS clients are created lazily when needed (e.g., S3Attribute, EncryptedAttribute).
/// They share the same configuration as the DynamoDB client.
///
/// # Examples
///
/// ```python
/// # Use environment variables or default chain
/// client = DynamoDBClient()
///
/// # Use hardcoded credentials
/// client = DynamoDBClient(
///     access_key="AKIA...",
///     secret_key="secret...",
///     region="us-east-1"
/// )
///
/// # Use AWS profile (supports SSO)
/// client = DynamoDBClient(profile="my-profile")
///
/// # Use local endpoint (localstack, moto)
/// client = DynamoDBClient(endpoint_url="http://localhost:4566")
///
/// # AssumeRole for cross-account access
/// client = DynamoDBClient(
///     role_arn="arn:aws:iam::123456789012:role/MyRole",
///     role_session_name="my-session"
/// )
///
/// # With timeouts and retries
/// client = DynamoDBClient(
///     connect_timeout=5.0,
///     read_timeout=30.0,
///     max_retries=3
/// )
/// ```
#[pyclass]
pub struct DynamoDBClient {
    /// DynamoDB client (always created)
    client: Client,
    /// Shared runtime for all AWS operations
    runtime: Arc<Runtime>,
    /// Effective region
    region: String,
    /// Shared config for lazy S3/KMS client creation
    config: Arc<AwsConfig>,
    /// S3 client (lazy, created on first S3 operation)
    s3_client: OnceCell<S3Client>,
    /// KMS client (lazy, created on first KMS operation)
    kms_client: OnceCell<KmsClient>,
}

#[pymethods]
impl DynamoDBClient {
    /// Create a new DynamoDB client.
    ///
    /// # Arguments
    ///
    /// * `region` - AWS region (default: us-east-1, or AWS_REGION env var)
    /// * `access_key` - AWS access key ID (optional)
    /// * `secret_key` - AWS secret access key (optional)
    /// * `session_token` - AWS session token for temporary credentials (optional)
    /// * `profile` - AWS profile name from ~/.aws/credentials (supports SSO profiles)
    /// * `endpoint_url` - Custom endpoint URL for local testing (optional)
    /// * `role_arn` - IAM role ARN for AssumeRole (optional)
    /// * `role_session_name` - Session name for AssumeRole (optional, default: "pydynox-session")
    /// * `external_id` - External ID for AssumeRole (optional)
    /// * `connect_timeout` - Connection timeout in seconds (optional)
    /// * `read_timeout` - Read timeout in seconds (optional)
    /// * `max_retries` - Maximum number of retries (optional, default: 3)
    /// * `proxy_url` - HTTP/HTTPS proxy URL (optional, e.g., "http://proxy:8080")
    ///
    /// # Returns
    ///
    /// A new DynamoDBClient instance.
    ///
    /// # Credential Resolution
    ///
    /// Credentials are resolved in this order:
    /// 1. Hardcoded (access_key + secret_key)
    /// 2. AssumeRole (if role_arn is set)
    /// 3. Profile (if profile is set, supports SSO)
    /// 4. Default chain (env vars, instance profile, container, WebIdentity, SSO)
    ///
    /// For EKS IRSA or GitHub Actions OIDC, just use `DynamoDBClient()` - the
    /// default chain handles WebIdentity automatically via env vars.
    #[new]
    #[pyo3(signature = (
        region=None,
        access_key=None,
        secret_key=None,
        session_token=None,
        profile=None,
        endpoint_url=None,
        role_arn=None,
        role_session_name=None,
        external_id=None,
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
        endpoint_url: Option<String>,
        role_arn: Option<String>,
        role_session_name: Option<String>,
        external_id: Option<String>,
        connect_timeout: Option<f64>,
        read_timeout: Option<f64>,
        max_retries: Option<u32>,
        proxy_url: Option<String>,
    ) -> PyResult<Self> {
        // Set proxy env var if provided (AWS SDK reads from env)
        if let Some(ref proxy) = proxy_url {
            std::env::set_var("HTTPS_PROXY", proxy);
        }

        let config = AwsConfig {
            region: region.clone(),
            access_key,
            secret_key,
            session_token,
            profile,
            endpoint_url,
            role_arn,
            role_session_name,
            external_id,
            connect_timeout,
            read_timeout,
            max_retries,
            proxy_url,
        };

        let runtime = RUNTIME.clone();
        let final_region = config.effective_region();

        let client = runtime
            .block_on(build_client(config.clone()))
            .map_err(|e| {
                PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!(
                    "Failed to create DynamoDB client: {}",
                    e
                ))
            })?;

        Ok(DynamoDBClient {
            client,
            runtime,
            region: final_region,
            config: Arc::new(config),
            s3_client: OnceCell::new(),
            kms_client: OnceCell::new(),
        })
    }

    /// Get the configured AWS region.
    pub fn get_region(&self) -> &str {
        &self.region
    }

    /// Check if the client can connect to DynamoDB.
    ///
    /// Makes a simple ListTables call to verify connectivity.
    /// Returns false if connection fails, true if successful.
    pub fn ping(&self) -> PyResult<bool> {
        let client = self.client.clone();
        let result = self
            .runtime
            .block_on(async { client.list_tables().limit(1).send().await });

        match result {
            Ok(_) => Ok(true),
            Err(_) => Ok(false),
        }
    }
    /// Put an item into a DynamoDB table.
    #[pyo3(signature = (table, item, condition_expression=None, expression_attribute_names=None, expression_attribute_values=None))]
    pub fn put_item(
        &self,
        py: Python<'_>,
        table: &str,
        item: &Bound<'_, PyDict>,
        condition_expression: Option<String>,
        expression_attribute_names: Option<&Bound<'_, PyDict>>,
        expression_attribute_values: Option<&Bound<'_, PyDict>>,
    ) -> PyResult<OperationMetrics> {
        basic_operations::put_item(
            py,
            &self.client,
            &self.runtime,
            table,
            item,
            condition_expression,
            expression_attribute_names,
            expression_attribute_values,
        )
    }

    /// Get an item from a DynamoDB table by its key.
    ///
    /// # Arguments
    ///
    /// * `table` - Table name
    /// * `key` - Key attributes as a dict
    /// * `consistent_read` - Use strongly consistent read
    /// * `projection` - List of attributes to return (saves RCU)
    /// * `expression_attribute_names` - Attribute name placeholders for reserved words
    ///
    /// # Returns
    ///
    /// Tuple of (item or None, metrics).
    #[pyo3(signature = (table, key, consistent_read=false, projection=None, expression_attribute_names=None))]
    pub fn get_item(
        &self,
        py: Python<'_>,
        table: &str,
        key: &Bound<'_, PyDict>,
        consistent_read: bool,
        projection: Option<String>,
        expression_attribute_names: Option<&Bound<'_, PyDict>>,
    ) -> PyResult<(Option<Py<PyAny>>, OperationMetrics)> {
        basic_operations::get_item(
            py,
            &self.client,
            &self.runtime,
            table,
            key,
            consistent_read,
            projection,
            expression_attribute_names,
        )
    }

    /// Delete an item from a DynamoDB table.
    #[pyo3(signature = (table, key, condition_expression=None, expression_attribute_names=None, expression_attribute_values=None))]
    pub fn delete_item(
        &self,
        py: Python<'_>,
        table: &str,
        key: &Bound<'_, PyDict>,
        condition_expression: Option<String>,
        expression_attribute_names: Option<&Bound<'_, PyDict>>,
        expression_attribute_values: Option<&Bound<'_, PyDict>>,
    ) -> PyResult<OperationMetrics> {
        basic_operations::delete_item(
            py,
            &self.client,
            &self.runtime,
            table,
            key,
            condition_expression,
            expression_attribute_names,
            expression_attribute_values,
        )
    }

    /// Update an item in a DynamoDB table.
    #[pyo3(signature = (table, key, updates=None, update_expression=None, condition_expression=None, expression_attribute_names=None, expression_attribute_values=None))]
    #[allow(clippy::too_many_arguments)]
    pub fn update_item(
        &self,
        py: Python<'_>,
        table: &str,
        key: &Bound<'_, PyDict>,
        updates: Option<&Bound<'_, PyDict>>,
        update_expression: Option<String>,
        condition_expression: Option<String>,
        expression_attribute_names: Option<&Bound<'_, PyDict>>,
        expression_attribute_values: Option<&Bound<'_, PyDict>>,
    ) -> PyResult<OperationMetrics> {
        basic_operations::update_item(
            py,
            &self.client,
            &self.runtime,
            table,
            key,
            updates,
            update_expression,
            condition_expression,
            expression_attribute_names,
            expression_attribute_values,
        )
    }

    /// Query a single page of items from a DynamoDB table.
    ///
    /// # Arguments
    ///
    /// * `table` - Table name
    /// * `key_condition_expression` - Key condition expression
    /// * `filter_expression` - Optional filter expression
    /// * `projection_expression` - Optional projection expression (saves RCU)
    /// * `expression_attribute_names` - Attribute name placeholders
    /// * `expression_attribute_values` - Attribute value placeholders
    /// * `limit` - Max items per page
    /// * `exclusive_start_key` - Start key for pagination
    /// * `scan_index_forward` - Sort order (true = ascending)
    /// * `index_name` - GSI or LSI name
    /// * `consistent_read` - Use strongly consistent read
    #[pyo3(signature = (table, key_condition_expression, filter_expression=None, projection_expression=None, expression_attribute_names=None, expression_attribute_values=None, limit=None, exclusive_start_key=None, scan_index_forward=None, index_name=None, consistent_read=false))]
    #[allow(clippy::too_many_arguments)]
    #[allow(clippy::type_complexity)]
    pub fn query_page(
        &self,
        py: Python<'_>,
        table: &str,
        key_condition_expression: &str,
        filter_expression: Option<String>,
        projection_expression: Option<String>,
        expression_attribute_names: Option<&Bound<'_, PyDict>>,
        expression_attribute_values: Option<&Bound<'_, PyDict>>,
        limit: Option<i32>,
        exclusive_start_key: Option<&Bound<'_, PyDict>>,
        scan_index_forward: Option<bool>,
        index_name: Option<String>,
        consistent_read: bool,
    ) -> PyResult<(Vec<Py<PyAny>>, Option<Py<PyAny>>, OperationMetrics)> {
        let result = basic_operations::query(
            py,
            &self.client,
            &self.runtime,
            table,
            key_condition_expression,
            filter_expression,
            projection_expression,
            expression_attribute_names,
            expression_attribute_values,
            limit,
            exclusive_start_key,
            scan_index_forward,
            index_name,
            consistent_read,
        )?;
        Ok((result.items, result.last_evaluated_key, result.metrics))
    }

    /// Scan a single page of items from a DynamoDB table.
    ///
    /// # Arguments
    ///
    /// * `table` - Table name
    /// * `filter_expression` - Optional filter expression
    /// * `projection_expression` - Optional projection expression (saves RCU)
    /// * `expression_attribute_names` - Attribute name placeholders
    /// * `expression_attribute_values` - Attribute value placeholders
    /// * `limit` - Max items per page
    /// * `exclusive_start_key` - Start key for pagination
    /// * `index_name` - GSI or LSI name
    /// * `consistent_read` - Use strongly consistent read
    /// * `segment` - Segment number for parallel scan
    /// * `total_segments` - Total segments for parallel scan
    #[pyo3(signature = (table, filter_expression=None, projection_expression=None, expression_attribute_names=None, expression_attribute_values=None, limit=None, exclusive_start_key=None, index_name=None, consistent_read=false, segment=None, total_segments=None))]
    #[allow(clippy::too_many_arguments)]
    #[allow(clippy::type_complexity)]
    pub fn scan_page(
        &self,
        py: Python<'_>,
        table: &str,
        filter_expression: Option<String>,
        projection_expression: Option<String>,
        expression_attribute_names: Option<&Bound<'_, PyDict>>,
        expression_attribute_values: Option<&Bound<'_, PyDict>>,
        limit: Option<i32>,
        exclusive_start_key: Option<&Bound<'_, PyDict>>,
        index_name: Option<String>,
        consistent_read: bool,
        segment: Option<i32>,
        total_segments: Option<i32>,
    ) -> PyResult<(Vec<Py<PyAny>>, Option<Py<PyAny>>, OperationMetrics)> {
        let result = basic_operations::scan(
            py,
            &self.client,
            &self.runtime,
            table,
            filter_expression,
            projection_expression,
            expression_attribute_names,
            expression_attribute_values,
            limit,
            exclusive_start_key,
            index_name,
            consistent_read,
            segment,
            total_segments,
        )?;
        Ok((result.items, result.last_evaluated_key, result.metrics))
    }

    /// Count items in a DynamoDB table.
    #[pyo3(signature = (table, filter_expression=None, expression_attribute_names=None, expression_attribute_values=None, index_name=None, consistent_read=false))]
    #[allow(clippy::too_many_arguments)]
    pub fn count(
        &self,
        py: Python<'_>,
        table: &str,
        filter_expression: Option<String>,
        expression_attribute_names: Option<&Bound<'_, PyDict>>,
        expression_attribute_values: Option<&Bound<'_, PyDict>>,
        index_name: Option<String>,
        consistent_read: bool,
    ) -> PyResult<(i64, OperationMetrics)> {
        basic_operations::count(
            py,
            &self.client,
            &self.runtime,
            table,
            filter_expression,
            expression_attribute_names,
            expression_attribute_values,
            index_name,
            consistent_read,
        )
    }

    /// Batch write items to a DynamoDB table.
    pub fn batch_write(
        &self,
        py: Python<'_>,
        table: &str,
        put_items: &Bound<'_, pyo3::types::PyList>,
        delete_keys: &Bound<'_, pyo3::types::PyList>,
    ) -> PyResult<()> {
        batch_operations::batch_write(
            py,
            &self.client,
            &self.runtime,
            table,
            put_items,
            delete_keys,
        )
    }

    /// Batch get items from a DynamoDB table.
    pub fn batch_get(
        &self,
        py: Python<'_>,
        table: &str,
        keys: &Bound<'_, pyo3::types::PyList>,
    ) -> PyResult<Vec<Py<PyAny>>> {
        batch_operations::batch_get(py, &self.client, &self.runtime, table, keys)
    }

    /// Execute a transactional write operation.
    pub fn transact_write(
        &self,
        py: Python<'_>,
        operations: &Bound<'_, pyo3::types::PyList>,
    ) -> PyResult<()> {
        transaction_operations::transact_write(py, &self.client, &self.runtime, operations)
    }

    /// Create a new DynamoDB table.
    #[pyo3(signature = (table_name, hash_key, range_key=None, billing_mode="PAY_PER_REQUEST", read_capacity=None, write_capacity=None, table_class=None, encryption=None, kms_key_id=None, global_secondary_indexes=None, local_secondary_indexes=None, wait=false))]
    #[allow(clippy::too_many_arguments)]
    pub fn create_table(
        &self,
        py: Python<'_>,
        table_name: &str,
        hash_key: (&str, &str),
        range_key: Option<(&str, &str)>,
        billing_mode: &str,
        read_capacity: Option<i64>,
        write_capacity: Option<i64>,
        table_class: Option<&str>,
        encryption: Option<&str>,
        kms_key_id: Option<&str>,
        global_secondary_indexes: Option<&Bound<'_, pyo3::types::PyList>>,
        local_secondary_indexes: Option<&Bound<'_, pyo3::types::PyList>>,
        wait: bool,
    ) -> PyResult<()> {
        let (range_key_name, range_key_type) = match range_key {
            Some((name, typ)) => (Some(name), Some(typ)),
            None => (None, None),
        };

        let gsis = match global_secondary_indexes {
            Some(list) => Some(table_operations::parse_gsi_definitions(py, list)?),
            None => None,
        };

        let lsis = match local_secondary_indexes {
            Some(list) => Some(table_operations::parse_lsi_definitions(py, list)?),
            None => None,
        };

        table_operations::create_table(
            &self.client,
            &self.runtime,
            table_name,
            hash_key.0,
            hash_key.1,
            range_key_name,
            range_key_type,
            billing_mode,
            read_capacity,
            write_capacity,
            table_class,
            encryption,
            kms_key_id,
            gsis,
            lsis,
            wait,
        )
    }

    /// Check if a table exists.
    pub fn table_exists(&self, table_name: &str) -> PyResult<bool> {
        table_operations::table_exists(&self.client, &self.runtime, table_name)
    }

    /// Delete a table.
    pub fn delete_table(&self, table_name: &str) -> PyResult<()> {
        table_operations::delete_table(&self.client, &self.runtime, table_name)
    }

    /// Wait for a table to become active.
    #[pyo3(signature = (table_name, timeout_seconds=None))]
    pub fn wait_for_table_active(
        &self,
        table_name: &str,
        timeout_seconds: Option<u64>,
    ) -> PyResult<()> {
        table_operations::wait_for_table_active(
            &self.client,
            &self.runtime,
            table_name,
            timeout_seconds,
        )
    }

    // ========== ASYNC METHODS ==========

    /// Async version of get_item.
    #[pyo3(signature = (table, key, consistent_read=false, projection=None, expression_attribute_names=None))]
    pub fn async_get_item<'py>(
        &self,
        py: Python<'py>,
        table: &str,
        key: &Bound<'_, PyDict>,
        consistent_read: bool,
        projection: Option<String>,
        expression_attribute_names: Option<&Bound<'_, PyDict>>,
    ) -> PyResult<Bound<'py, PyAny>> {
        basic_operations::async_get_item(
            py,
            self.client.clone(),
            table,
            key,
            consistent_read,
            projection,
            expression_attribute_names,
        )
    }

    /// Async version of put_item.
    #[pyo3(signature = (table, item, condition_expression=None, expression_attribute_names=None, expression_attribute_values=None))]
    pub fn async_put_item<'py>(
        &self,
        py: Python<'py>,
        table: &str,
        item: &Bound<'_, PyDict>,
        condition_expression: Option<String>,
        expression_attribute_names: Option<&Bound<'_, PyDict>>,
        expression_attribute_values: Option<&Bound<'_, PyDict>>,
    ) -> PyResult<Bound<'py, PyAny>> {
        basic_operations::async_put_item(
            py,
            self.client.clone(),
            table,
            item,
            condition_expression,
            expression_attribute_names,
            expression_attribute_values,
        )
    }

    /// Async version of delete_item.
    #[pyo3(signature = (table, key, condition_expression=None, expression_attribute_names=None, expression_attribute_values=None))]
    pub fn async_delete_item<'py>(
        &self,
        py: Python<'py>,
        table: &str,
        key: &Bound<'_, PyDict>,
        condition_expression: Option<String>,
        expression_attribute_names: Option<&Bound<'_, PyDict>>,
        expression_attribute_values: Option<&Bound<'_, PyDict>>,
    ) -> PyResult<Bound<'py, PyAny>> {
        basic_operations::async_delete_item(
            py,
            self.client.clone(),
            table,
            key,
            condition_expression,
            expression_attribute_names,
            expression_attribute_values,
        )
    }

    /// Async version of update_item.
    #[pyo3(signature = (table, key, updates=None, update_expression=None, condition_expression=None, expression_attribute_names=None, expression_attribute_values=None))]
    #[allow(clippy::too_many_arguments)]
    pub fn async_update_item<'py>(
        &self,
        py: Python<'py>,
        table: &str,
        key: &Bound<'_, PyDict>,
        updates: Option<&Bound<'_, PyDict>>,
        update_expression: Option<String>,
        condition_expression: Option<String>,
        expression_attribute_names: Option<&Bound<'_, PyDict>>,
        expression_attribute_values: Option<&Bound<'_, PyDict>>,
    ) -> PyResult<Bound<'py, PyAny>> {
        basic_operations::async_update_item(
            py,
            self.client.clone(),
            table,
            key,
            updates,
            update_expression,
            condition_expression,
            expression_attribute_names,
            expression_attribute_values,
        )
    }

    /// Async version of query_page.
    #[pyo3(signature = (table, key_condition_expression, filter_expression=None, projection_expression=None, expression_attribute_names=None, expression_attribute_values=None, limit=None, exclusive_start_key=None, scan_index_forward=None, index_name=None, consistent_read=false))]
    #[allow(clippy::too_many_arguments)]
    pub fn async_query_page<'py>(
        &self,
        py: Python<'py>,
        table: &str,
        key_condition_expression: &str,
        filter_expression: Option<String>,
        projection_expression: Option<String>,
        expression_attribute_names: Option<&Bound<'_, PyDict>>,
        expression_attribute_values: Option<&Bound<'_, PyDict>>,
        limit: Option<i32>,
        exclusive_start_key: Option<&Bound<'_, PyDict>>,
        scan_index_forward: Option<bool>,
        index_name: Option<String>,
        consistent_read: bool,
    ) -> PyResult<Bound<'py, PyAny>> {
        basic_operations::async_query(
            py,
            self.client.clone(),
            table,
            key_condition_expression,
            filter_expression,
            projection_expression,
            expression_attribute_names,
            expression_attribute_values,
            limit,
            exclusive_start_key,
            scan_index_forward,
            index_name,
            consistent_read,
        )
    }

    /// Async version of scan_page.
    #[pyo3(signature = (table, filter_expression=None, projection_expression=None, expression_attribute_names=None, expression_attribute_values=None, limit=None, exclusive_start_key=None, index_name=None, consistent_read=false, segment=None, total_segments=None))]
    #[allow(clippy::too_many_arguments)]
    pub fn async_scan_page<'py>(
        &self,
        py: Python<'py>,
        table: &str,
        filter_expression: Option<String>,
        projection_expression: Option<String>,
        expression_attribute_names: Option<&Bound<'_, PyDict>>,
        expression_attribute_values: Option<&Bound<'_, PyDict>>,
        limit: Option<i32>,
        exclusive_start_key: Option<&Bound<'_, PyDict>>,
        index_name: Option<String>,
        consistent_read: bool,
        segment: Option<i32>,
        total_segments: Option<i32>,
    ) -> PyResult<Bound<'py, PyAny>> {
        basic_operations::async_scan(
            py,
            self.client.clone(),
            table,
            filter_expression,
            projection_expression,
            expression_attribute_names,
            expression_attribute_values,
            limit,
            exclusive_start_key,
            index_name,
            consistent_read,
            segment,
            total_segments,
        )
    }

    /// Async version of count.
    #[pyo3(signature = (table, filter_expression=None, expression_attribute_names=None, expression_attribute_values=None, index_name=None, consistent_read=false))]
    #[allow(clippy::too_many_arguments)]
    pub fn async_count<'py>(
        &self,
        py: Python<'py>,
        table: &str,
        filter_expression: Option<String>,
        expression_attribute_names: Option<&Bound<'_, PyDict>>,
        expression_attribute_values: Option<&Bound<'_, PyDict>>,
        index_name: Option<String>,
        consistent_read: bool,
    ) -> PyResult<Bound<'py, PyAny>> {
        basic_operations::async_count(
            py,
            self.client.clone(),
            table,
            filter_expression,
            expression_attribute_names,
            expression_attribute_values,
            index_name,
            consistent_read,
        )
    }

    /// Parallel scan - runs multiple segment scans concurrently.
    ///
    /// This is much faster than regular scan for large tables.
    /// Each segment is scanned in parallel using tokio tasks.
    ///
    /// # Arguments
    ///
    /// * `table` - Table name
    /// * `total_segments` - Number of parallel segments (1-1000000)
    /// * `filter_expression` - Optional filter expression
    /// * `projection_expression` - Optional projection expression (saves RCU)
    /// * `expression_attribute_names` - Attribute name placeholders
    /// * `expression_attribute_values` - Attribute value placeholders
    /// * `consistent_read` - Use strongly consistent reads
    ///
    /// # Returns
    ///
    /// Tuple of (items, metrics) where items is a list of all scanned items.
    #[pyo3(signature = (table, total_segments, filter_expression=None, projection_expression=None, expression_attribute_names=None, expression_attribute_values=None, consistent_read=false))]
    #[allow(clippy::too_many_arguments)]
    pub fn parallel_scan(
        &self,
        py: Python<'_>,
        table: &str,
        total_segments: i32,
        filter_expression: Option<String>,
        projection_expression: Option<String>,
        expression_attribute_names: Option<&Bound<'_, PyDict>>,
        expression_attribute_values: Option<&Bound<'_, PyDict>>,
        consistent_read: bool,
    ) -> PyResult<(Vec<Py<PyAny>>, OperationMetrics)> {
        basic_operations::parallel_scan(
            py,
            &self.client,
            &self.runtime,
            table,
            total_segments,
            filter_expression,
            projection_expression,
            expression_attribute_names,
            expression_attribute_values,
            consistent_read,
        )
    }

    /// Async version of parallel_scan.
    #[pyo3(signature = (table, total_segments, filter_expression=None, projection_expression=None, expression_attribute_names=None, expression_attribute_values=None, consistent_read=false))]
    #[allow(clippy::too_many_arguments)]
    pub fn async_parallel_scan<'py>(
        &self,
        py: Python<'py>,
        table: &str,
        total_segments: i32,
        filter_expression: Option<String>,
        projection_expression: Option<String>,
        expression_attribute_names: Option<&Bound<'_, PyDict>>,
        expression_attribute_values: Option<&Bound<'_, PyDict>>,
        consistent_read: bool,
    ) -> PyResult<Bound<'py, PyAny>> {
        basic_operations::async_parallel_scan(
            py,
            self.client.clone(),
            table,
            total_segments,
            filter_expression,
            projection_expression,
            expression_attribute_names,
            expression_attribute_values,
            consistent_read,
        )
    }

    // ========== PARTIQL OPERATIONS ==========

    /// Execute a PartiQL statement.
    #[pyo3(signature = (statement, parameters=None, consistent_read=false, next_token=None))]
    pub fn execute_statement(
        &self,
        py: Python<'_>,
        statement: &str,
        parameters: Option<&Bound<'_, pyo3::types::PyList>>,
        consistent_read: bool,
        next_token: Option<String>,
    ) -> PyResult<(Vec<Py<PyAny>>, Option<String>, OperationMetrics)> {
        basic_operations::execute_statement(
            py,
            &self.client,
            &self.runtime,
            statement,
            parameters,
            consistent_read,
            next_token,
        )
    }

    /// Async version of execute_statement.
    #[pyo3(signature = (statement, parameters=None, consistent_read=false, next_token=None))]
    pub fn async_execute_statement<'py>(
        &self,
        py: Python<'py>,
        statement: &str,
        parameters: Option<&Bound<'_, pyo3::types::PyList>>,
        consistent_read: bool,
        next_token: Option<String>,
    ) -> PyResult<Bound<'py, PyAny>> {
        basic_operations::async_execute_statement(
            py,
            self.client.clone(),
            statement.to_string(),
            parameters,
            consistent_read,
            next_token,
        )
    }
}

// ========== INTERNAL METHODS (not exposed to Python) ==========

impl DynamoDBClient {
    /// Get or create the S3 client (lazy initialization).
    ///
    /// The S3 client shares the same config as DynamoDB.
    /// Created on first use to avoid overhead when S3 is not needed.
    pub fn get_s3_client(&self) -> PyResult<&S3Client> {
        self.s3_client.get_or_try_init(|| {
            self.runtime
                .block_on(build_s3_client(&self.config, None))
                .map_err(|e| {
                    PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!(
                        "Failed to create S3 client: {}",
                        e
                    ))
                })
        })
    }

    /// Get or create the KMS client (lazy initialization).
    ///
    /// The KMS client shares the same config as DynamoDB.
    /// Created on first use to avoid overhead when KMS is not needed.
    pub fn get_kms_client(&self) -> PyResult<&KmsClient> {
        self.kms_client.get_or_try_init(|| {
            self.runtime
                .block_on(build_kms_client(&self.config, None))
                .map_err(|e| {
                    PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!(
                        "Failed to create KMS client: {}",
                        e
                    ))
                })
        })
    }

    /// Get the shared runtime.
    pub fn get_runtime(&self) -> &Arc<Runtime> {
        &self.runtime
    }

    /// Get the shared config.
    pub fn get_config(&self) -> &Arc<AwsConfig> {
        &self.config
    }
}
