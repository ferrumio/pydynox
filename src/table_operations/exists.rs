//! Table existence check operation.

use aws_sdk_dynamodb::Client;
use pyo3::prelude::*;
use std::sync::Arc;
use tokio::runtime::Runtime;

use crate::errors::map_sdk_error;

/// Check if a table exists.
///
/// # Arguments
///
/// * `client` - The DynamoDB client
/// * `runtime` - The Tokio runtime
/// * `table_name` - Name of the table to check
///
/// # Returns
///
/// True if the table exists, false otherwise.
pub fn table_exists(client: &Client, runtime: &Arc<Runtime>, table_name: &str) -> PyResult<bool> {
    let client = client.clone();
    let table_name = table_name.to_string();

    runtime.block_on(async {
        match client.describe_table().table_name(&table_name).send().await {
            Ok(_) => Ok(true),
            Err(e) => {
                // Check if it's a service error (ResourceNotFoundException)
                if let Some(service_error) = e.as_service_error() {
                    if service_error.is_resource_not_found_exception() {
                        return Ok(false);
                    }
                }
                // For any other error, use map_sdk_error
                Err(map_sdk_error(e, Some(&table_name)))
            }
        }
    })
}
