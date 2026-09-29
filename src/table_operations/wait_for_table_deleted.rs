//! Wait for table to be deleted.

use aws_sdk_dynamodb::Client;
use aws_sdk_dynamodb::types::TableStatus;
use pyo3::prelude::*;
use std::sync::Arc;
use std::time::Duration;
use tokio::runtime::Runtime;

use crate::errors::map_sdk_error;

/// Execute wait_for_table_deleted asynchronously.
pub async fn execute_wait_for_table_deleted(
    client: Client,
    table_name: &str,
    timeout_seconds: Option<u64>,
) -> PyResult<()> {
    let timeout = timeout_seconds.unwrap_or(60);
    let start = std::time::Instant::now();
    let poll_interval = Duration::from_millis(500);

    loop {
        if start.elapsed().as_secs() > timeout {
            return Err(PyErr::new::<pyo3::exceptions::PyTimeoutError, _>(format!(
                "Timeout waiting for table '{}' to be deleted",
                table_name
            )));
        }

        let result = client.describe_table().table_name(table_name).send().await;

        match result {
            Ok(response) => {
                // Table exists, check if it has been deleted
                if let Some(table) = response.table() {
                    // Check if table is in a status that suggests deletion
                    match table.table_status() {
                        // If the table is actively deleting, wait some more
                        Some(TableStatus::Deleting) => {
                            // Continue waiting
                        }
                        // If table is active, it might not be fully deleted yet
                        Some(TableStatus::Active) => {
                            // This should not really happen in normal operation,
                            // but if it happens, it means deletion didn't actually occur.
                            // We'll treat this case as if we're still waiting
                        }
                        // Other statuses (Inactive,Archiving, etc.) - we should just keep waiting
                        _ => {
                            // Continue waiting for table to be fully gone
                        }
                    }
                }
            }
            Err(e) => {
                // Check if it's ResourceNotFoundException (table is gone)
                if let Some(service_error) = e.as_service_error() {
                    if service_error.is_resource_not_found_exception() {
                        // Table successfully deleted
                        return Ok(());
                    }

                    // If it's a service error that's not resource not found, propagate it
                    return Err(map_sdk_error(e, Some(table_name)));
                } else {
                    // If it's not a service error, treat as error
                    return Err(map_sdk_error(e, Some(table_name)));
                }
            }
        }

        tokio::time::sleep(poll_interval).await;
    }
}

/// Async wait_for_table_deleted - returns a Python awaitable.
pub fn wait_for_table_deleted<'py>(
    py: Python<'py>,
    client: Client,
    table_name: &str,
    timeout_seconds: Option<u64>,
) -> PyResult<Bound<'py, PyAny>> {
    let table_name = table_name.to_string();

    pyo3_async_runtimes::tokio::future_into_py(py, async move {
        execute_wait_for_table_deleted(client, &table_name, timeout_seconds).await
    })
}

/// Sync wait_for_table_deleted - blocks until complete.
pub fn sync_wait_for_table_deleted(
    client: &Client,
    runtime: &Arc<Runtime>,
    table_name: &str,
    timeout_seconds: Option<u64>,
) -> PyResult<()> {
    let client = client.clone();
    let table_name = table_name.to_string();

    runtime.block_on(async {
        execute_wait_for_table_deleted(client, &table_name, timeout_seconds).await
    })
}