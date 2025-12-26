//! DynamoDB client module.
//!
//! Provides a flexible DynamoDB client that supports multiple credential sources:
//! - Environment variables
//! - Hardcoded credentials
//! - AWS profiles

use aws_config::meta::region::RegionProviderChain;
use aws_config::profile::ProfileFileCredentialsProvider;
use aws_config::BehaviorVersion;
use aws_sdk_dynamodb::config::Credentials;
use aws_sdk_dynamodb::Client;
use pyo3::prelude::*;
use std::sync::Arc;
use tokio::runtime::Runtime;

/// DynamoDB client with flexible credential configuration.
///
/// Supports multiple credential sources in order of priority:
/// 1. Hardcoded credentials (access_key, secret_key, session_token)
/// 2. AWS profile from ~/.aws/credentials
/// 3. Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN)
/// 4. Default credential chain (instance profile, etc.)
///
/// # Examples
///
/// ```python
/// # Use environment variables
/// client = DynamoClient()
///
/// # Use hardcoded credentials
/// client = DynamoClient(
///     access_key="AKIA...",
///     secret_key="secret...",
///     region="us-east-1"
/// )
///
/// # Use AWS profile
/// client = DynamoClient(profile="my-profile")
///
/// # Use local endpoint (localstack, moto)
/// client = DynamoClient(endpoint_url="http://localhost:4566")
/// ```
#[pyclass]
pub struct DynamoClient {
    /// The underlying AWS SDK DynamoDB client.
    client: Client,
    /// Tokio runtime for async operations.
    runtime: Arc<Runtime>,
    /// The configured AWS region.
    region: String,
}

#[pymethods]
impl DynamoClient {
    /// Create a new DynamoDB client.
    ///
    /// # Arguments
    ///
    /// * `region` - AWS region (default: us-east-1, or AWS_REGION env var)
    /// * `access_key` - AWS access key ID (optional, uses env/profile if not set)
    /// * `secret_key` - AWS secret access key (optional, uses env/profile if not set)
    /// * `session_token` - AWS session token for temporary credentials (optional)
    /// * `profile` - AWS profile name from ~/.aws/credentials (optional)
    /// * `endpoint_url` - Custom endpoint URL for local testing (optional)
    ///
    /// # Returns
    ///
    /// A new DynamoClient instance.
    ///
    /// # Errors
    ///
    /// Returns an error if the client cannot be created (e.g., invalid credentials).
    #[new]
    #[pyo3(signature = (region=None, access_key=None, secret_key=None, session_token=None, profile=None, endpoint_url=None))]
    pub fn new(
        region: Option<String>,
        access_key: Option<String>,
        secret_key: Option<String>,
        session_token: Option<String>,
        profile: Option<String>,
        endpoint_url: Option<String>,
    ) -> PyResult<Self> {
        let runtime = Runtime::new().map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!(
                "Failed to create tokio runtime: {}",
                e
            ))
        })?;

        let client = runtime
            .block_on(async {
                build_client(
                    region.clone(),
                    access_key,
                    secret_key,
                    session_token,
                    profile,
                    endpoint_url,
                )
                .await
            })
            .map_err(|e| {
                PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!(
                    "Failed to create DynamoDB client: {}",
                    e
                ))
            })?;

        let final_region = region.unwrap_or_else(|| {
            std::env::var("AWS_REGION")
                .or_else(|_| std::env::var("AWS_DEFAULT_REGION"))
                .unwrap_or_else(|_| "us-east-1".to_string())
        });

        Ok(DynamoClient {
            client,
            runtime: Arc::new(runtime),
            region: final_region,
        })
    }

    /// Get the configured AWS region.
    ///
    /// # Returns
    ///
    /// The region string (e.g., "us-east-1").
    pub fn get_region(&self) -> &str {
        &self.region
    }

    /// Check if the client can connect to DynamoDB.
    ///
    /// Makes a simple ListTables call to verify connectivity.
    ///
    /// # Returns
    ///
    /// True if connection is successful.
    ///
    /// # Errors
    ///
    /// Returns a ConnectionError if the connection fails.
    pub fn ping(&self) -> PyResult<bool> {
        let client = self.client.clone();
        let result = self
            .runtime
            .block_on(async { client.list_tables().limit(1).send().await });

        match result {
            Ok(_) => Ok(true),
            Err(e) => Err(PyErr::new::<pyo3::exceptions::PyConnectionError, _>(
                format!("Failed to connect to DynamoDB: {}", e),
            )),
        }
    }
}

/// Build the AWS SDK DynamoDB client with the given configuration.
///
/// # Arguments
///
/// * `region` - Optional AWS region
/// * `access_key` - Optional AWS access key ID
/// * `secret_key` - Optional AWS secret access key
/// * `session_token` - Optional AWS session token
/// * `profile` - Optional AWS profile name
/// * `endpoint_url` - Optional custom endpoint URL
///
/// # Returns
///
/// A configured DynamoDB Client.
async fn build_client(
    region: Option<String>,
    access_key: Option<String>,
    secret_key: Option<String>,
    session_token: Option<String>,
    profile: Option<String>,
    endpoint_url: Option<String>,
) -> Result<Client, String> {
    // Region priority: param > env var > default
    let region_provider =
        RegionProviderChain::first_try(region.map(aws_sdk_dynamodb::config::Region::new))
            .or_default_provider()
            .or_else("us-east-1");

    let mut config_loader = aws_config::defaults(BehaviorVersion::latest()).region(region_provider);

    // Credentials priority: hardcoded > profile > env/default chain
    if let (Some(ak), Some(sk)) = (access_key, secret_key) {
        let creds = Credentials::new(ak, sk, session_token, None, "pydyno-hardcoded");
        config_loader = config_loader.credentials_provider(creds);
    } else if let Some(profile_name) = profile {
        let profile_provider = ProfileFileCredentialsProvider::builder()
            .profile_name(&profile_name)
            .build();
        config_loader = config_loader.credentials_provider(profile_provider);
    }
    // else: uses default credential chain (env vars, instance profile, etc)

    let sdk_config = config_loader.load().await;

    let mut dynamo_config = aws_sdk_dynamodb::config::Builder::from(&sdk_config);

    if let Some(url) = endpoint_url {
        dynamo_config = dynamo_config.endpoint_url(url);
    }

    Ok(Client::from_conf(dynamo_config.build()))
}
