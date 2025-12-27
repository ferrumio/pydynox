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
use pyo3::types::PyDict;
use std::sync::Arc;
use tokio::runtime::Runtime;

use crate::basic_operations;
use crate::batch_operations;

/// DynamoDB client with flexible credential configuration.
///
/// Supports multiple credential sources in order of priority:
/// 1. Hardcoded credentials (access_key, secret_key, session_token)
/// 2. AWS profile from ~/.aws/credentials
/// 3. Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
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
    client: Client,
    runtime: Arc<Runtime>,
    region: String,
}

#[pymethods]
impl DynamoClient {
    /// Create a new DynamoDB client.
    ///
    /// # Arguments
    ///
    /// * `region` - AWS region (default: us-east-1, or AWS_REGION env var)
    /// * `access_key` - AWS access key ID (optional)
    /// * `secret_key` - AWS secret access key (optional)
    /// * `session_token` - AWS session token for temporary credentials (optional)
    /// * `profile` - AWS profile name from ~/.aws/credentials (optional)
    /// * `endpoint_url` - Custom endpoint URL for local testing (optional)
    ///
    /// # Returns
    ///
    /// A new DynamoClient instance.
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
    pub fn get_region(&self) -> &str {
        &self.region
    }

    /// Check if the client can connect to DynamoDB.
    ///
    /// Makes a simple ListTables call to verify connectivity.
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

    /// Put an item into a DynamoDB table.
    ///
    /// # Arguments
    ///
    /// * `table` - The name of the DynamoDB table
    /// * `item` - A Python dict representing the item to save
    ///
    /// # Examples
    ///
    /// ```python
    /// client = DynamoClient()
    /// client.put_item("users", {"pk": "USER#123", "name": "John", "age": 30})
    /// ```
    pub fn put_item(&self, py: Python<'_>, table: &str, item: &Bound<'_, PyDict>) -> PyResult<()> {
        basic_operations::put_item(py, &self.client, &self.runtime, table, item)
    }

    /// Get an item from a DynamoDB table by its key.
    ///
    /// # Arguments
    ///
    /// * `table` - The name of the DynamoDB table
    /// * `key` - A Python dict with the key attributes (hash key and optional range key)
    ///
    /// # Returns
    ///
    /// The item as a Python dict if found, None if not found.
    ///
    /// # Examples
    ///
    /// ```python
    /// client = DynamoClient()
    /// item = client.get_item("users", {"pk": "USER#123"})
    /// if item:
    ///     print(item["name"])  # "John"
    /// ```
    pub fn get_item(
        &self,
        py: Python<'_>,
        table: &str,
        key: &Bound<'_, PyDict>,
    ) -> PyResult<Option<Py<PyAny>>> {
        basic_operations::get_item(py, &self.client, &self.runtime, table, key)
    }

    /// Delete an item from a DynamoDB table.
    ///
    /// # Arguments
    ///
    /// * `table` - The name of the DynamoDB table
    /// * `key` - A Python dict with the key attributes (hash key and optional range key)
    /// * `condition_expression` - Optional condition expression string
    /// * `expression_attribute_names` - Optional dict mapping name placeholders to attribute names
    /// * `expression_attribute_values` - Optional dict mapping value placeholders to values
    ///
    /// # Returns
    ///
    /// None on success. Raises an exception if the condition fails or other errors occur.
    ///
    /// # Examples
    ///
    /// ```python
    /// client = DynamoClient()
    ///
    /// # Simple delete
    /// client.delete_item("users", {"pk": "USER#123"})
    ///
    /// # Delete with condition
    /// client.delete_item(
    ///     "users",
    ///     {"pk": "USER#123"},
    ///     condition_expression="attribute_exists(#pk)",
    ///     expression_attribute_names={"#pk": "pk"}
    /// )
    /// ```
    #[pyo3(signature = (table, key, condition_expression=None, expression_attribute_names=None, expression_attribute_values=None))]
    pub fn delete_item(
        &self,
        py: Python<'_>,
        table: &str,
        key: &Bound<'_, PyDict>,
        condition_expression: Option<String>,
        expression_attribute_names: Option<&Bound<'_, PyDict>>,
        expression_attribute_values: Option<&Bound<'_, PyDict>>,
    ) -> PyResult<()> {
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
    ///
    /// Supports two modes:
    /// 1. Simple updates via `updates` dict - sets field values directly
    /// 2. Complex updates via `update_expression` - full DynamoDB update expression
    ///
    /// # Arguments
    ///
    /// * `table` - The name of the DynamoDB table
    /// * `key` - A Python dict with the key attributes (hash key and optional range key)
    /// * `updates` - Optional dict of field:value pairs for simple SET updates
    /// * `update_expression` - Optional full update expression string
    /// * `condition_expression` - Optional condition expression string
    /// * `expression_attribute_names` - Optional dict mapping name placeholders to attribute names
    /// * `expression_attribute_values` - Optional dict mapping value placeholders to values
    ///
    /// # Returns
    ///
    /// None on success. Raises an exception if the condition fails or other errors occur.
    ///
    /// # Examples
    ///
    /// ```python
    /// client = DynamoClient()
    ///
    /// # Simple update - set fields
    /// client.update_item("users", {"pk": "USER#123"}, updates={"name": "John", "age": 31})
    ///
    /// # Atomic increment
    /// client.update_item(
    ///     "users",
    ///     {"pk": "USER#123"},
    ///     update_expression="SET #c = #c + :val",
    ///     expression_attribute_names={"#c": "counter"},
    ///     expression_attribute_values={":val": 1}
    /// )
    ///
    /// # Update with condition
    /// client.update_item(
    ///     "users",
    ///     {"pk": "USER#123"},
    ///     updates={"status": "active"},
    ///     condition_expression="attribute_exists(#pk)",
    ///     expression_attribute_names={"#pk": "pk"}
    /// )
    /// ```
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
    ) -> PyResult<()> {
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
    /// This is the internal method that returns a single page of results.
    /// For automatic pagination, use the `query()` method from Python which
    /// returns an iterator.
    ///
    /// # Arguments
    ///
    /// * `table` - The name of the DynamoDB table
    /// * `key_condition_expression` - Key condition expression (e.g., "#pk = :pk")
    /// * `filter_expression` - Optional filter expression for non-key attributes
    /// * `expression_attribute_names` - Dict mapping name placeholders to attribute names
    /// * `expression_attribute_values` - Dict mapping value placeholders to values
    /// * `limit` - Optional max number of items to return
    /// * `exclusive_start_key` - Optional key to start from (for pagination)
    /// * `scan_index_forward` - Sort order (True = ascending, False = descending)
    /// * `index_name` - Optional GSI or LSI name to query
    ///
    /// # Returns
    ///
    /// A tuple of (items, last_evaluated_key). Items is a list of dicts.
    /// last_evaluated_key is None if there are no more items, or a dict to pass
    /// as exclusive_start_key for the next page.
    #[pyo3(signature = (table, key_condition_expression, filter_expression=None, expression_attribute_names=None, expression_attribute_values=None, limit=None, exclusive_start_key=None, scan_index_forward=None, index_name=None))]
    #[allow(clippy::too_many_arguments)]
    pub fn query_page(
        &self,
        py: Python<'_>,
        table: &str,
        key_condition_expression: &str,
        filter_expression: Option<String>,
        expression_attribute_names: Option<&Bound<'_, PyDict>>,
        expression_attribute_values: Option<&Bound<'_, PyDict>>,
        limit: Option<i32>,
        exclusive_start_key: Option<&Bound<'_, PyDict>>,
        scan_index_forward: Option<bool>,
        index_name: Option<String>,
    ) -> PyResult<(Vec<Py<PyAny>>, Option<Py<PyAny>>)> {
        let result = basic_operations::query(
            py,
            &self.client,
            &self.runtime,
            table,
            key_condition_expression,
            filter_expression,
            expression_attribute_names,
            expression_attribute_values,
            limit,
            exclusive_start_key,
            scan_index_forward,
            index_name,
        )?;
        Ok((result.items, result.last_evaluated_key))
    }

    /// Batch write items to a DynamoDB table.
    ///
    /// Writes multiple items in a single request. Handles:
    /// - Splitting requests to respect the 25-item limit per batch
    /// - Retrying unprocessed items with exponential backoff
    ///
    /// # Arguments
    ///
    /// * `table` - The name of the DynamoDB table
    /// * `put_items` - List of items to put (as dicts)
    /// * `delete_keys` - List of keys to delete (as dicts)
    ///
    /// # Examples
    ///
    /// ```python
    /// client = DynamoClient()
    ///
    /// # Batch put items
    /// client.batch_write(
    ///     "users",
    ///     put_items=[
    ///         {"pk": "USER#1", "sk": "PROFILE", "name": "Alice"},
    ///         {"pk": "USER#2", "sk": "PROFILE", "name": "Bob"},
    ///     ],
    ///     delete_keys=[]
    /// )
    ///
    /// # Batch delete items
    /// client.batch_write(
    ///     "users",
    ///     put_items=[],
    ///     delete_keys=[
    ///         {"pk": "USER#3", "sk": "PROFILE"},
    ///         {"pk": "USER#4", "sk": "PROFILE"},
    ///     ]
    /// )
    ///
    /// # Mixed put and delete
    /// client.batch_write(
    ///     "users",
    ///     put_items=[{"pk": "USER#1", "sk": "PROFILE", "name": "Alice"}],
    ///     delete_keys=[{"pk": "USER#2", "sk": "PROFILE"}]
    /// )
    /// ```
    pub fn batch_write(
        &self,
        py: Python<'_>,
        table: &str,
        put_items: &Bound<'_, pyo3::types::PyList>,
        delete_keys: &Bound<'_, pyo3::types::PyList>,
    ) -> PyResult<()> {
        batch_operations::batch_write(py, &self.client, &self.runtime, table, put_items, delete_keys)
    }
}

/// Build the AWS SDK DynamoDB client with the given configuration.
async fn build_client(
    region: Option<String>,
    access_key: Option<String>,
    secret_key: Option<String>,
    session_token: Option<String>,
    profile: Option<String>,
    endpoint_url: Option<String>,
) -> Result<Client, String> {
    let region_provider =
        RegionProviderChain::first_try(region.map(aws_sdk_dynamodb::config::Region::new))
            .or_default_provider()
            .or_else("us-east-1");

    let mut config_loader = aws_config::defaults(BehaviorVersion::latest()).region(region_provider);

    // Credentials priority: hardcoded > profile > env/default chain
    if let (Some(ak), Some(sk)) = (access_key, secret_key) {
        let creds = Credentials::new(ak, sk, session_token, None, "pydynox-hardcoded");
        config_loader = config_loader.credentials_provider(creds);
    } else if let Some(profile_name) = profile {
        let profile_provider = ProfileFileCredentialsProvider::builder()
            .profile_name(&profile_name)
            .build();
        config_loader = config_loader.credentials_provider(profile_provider);
    }

    let sdk_config = config_loader.load().await;

    let mut dynamo_config = aws_sdk_dynamodb::config::Builder::from(&sdk_config);

    if let Some(url) = endpoint_url {
        dynamo_config = dynamo_config.endpoint_url(url);
    }

    Ok(Client::from_conf(dynamo_config.build()))
}
