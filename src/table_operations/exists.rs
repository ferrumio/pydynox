//! Table existence check operation.

use aws_sdk_dynamodb::Client;
use pyo3::prelude::*;
use std::sync::Arc;
use tokio::runtime::Runtime;

use crate::errors::map_sdk_error;

/// Execute table_exists asynchronously.
pub async fn execute_table_exists(client: Client, table_name: String) -> PyResult<bool> {
    match client.describe_table().table_name(&table_name).send().await {
        Ok(_) => Ok(true),
        Err(e) => {
            // Check if it's ResourceNotFoundException
            if let Some(service_error) = e.as_service_error() {
                if service_error.is_resource_not_found_exception() {
                    return Ok(false);
                }
            }
            // For any other error, use map_sdk_error
            Err(map_sdk_error(e, Some(&table_name)))
        }
    }
}

/// Async table_exists - returns a Python awaitable.
pub fn table_exists<'py>(
    py: Python<'py>,
    client: Client,
    table_name: &str,
) -> PyResult<Bound<'py, PyAny>> {
    let table_name = table_name.to_string();

    pyo3_async_runtimes::tokio::future_into_py(py, async move {
        execute_table_exists(client, table_name).await
    })
}

/// Sync table_exists - blocks until complete.
pub fn sync_table_exists(
    client: &Client,
    runtime: &Arc<Runtime>,
    table_name: &str,
) -> PyResult<bool> {
    let client = client.clone();
    let table_name = table_name.to_string();

    runtime.block_on(async { execute_table_exists(client, table_name).await })
}
