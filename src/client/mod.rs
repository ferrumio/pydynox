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

mod basic_ops;
mod batch_ops;
mod partiql_ops;
mod query_ops;
mod table_ops;
mod transaction_ops;

use aws_sdk_dynamodb::Client;
use aws_sdk_kms::Client as KmsClient;
use aws_sdk_s3::Client as S3Client;
use once_cell::sync::{Lazy, OnceCell};
use pyo3::prelude::*;
use std::sync::Arc;
use tokio::runtime::Runtime;

use crate::client_internal::{AwsConfig, build_client, build_kms_client, build_s3_client};

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
    pub(crate) client: Client,
    /// Shared runtime for all AWS operations
    pub(crate) runtime: Arc<Runtime>,
    /// Effective region
    pub(crate) region: String,
    /// Shared config for lazy S3/KMS client creation
    #[allow(dead_code)]
    pub(crate) config: Arc<AwsConfig>,
    /// S3 client (lazy, created on first S3 operation)
    #[allow(dead_code)]
    pub(crate) s3_client: OnceCell<S3Client>,
    /// KMS client (lazy, created on first KMS operation)
    #[allow(dead_code)]
    pub(crate) kms_client: OnceCell<KmsClient>,
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
            // SAFETY: called during client construction, before any async work starts
            unsafe { std::env::set_var("HTTPS_PROXY", proxy) };
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
}

// ========== INTERNAL METHODS (not exposed to Python) ==========

#[allow(dead_code)]
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
