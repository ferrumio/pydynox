//! Wait for table to become active.

use aws_sdk_dynamodb::types::TableStatus;
use aws_sdk_dynamodb::Client;
use pyo3::prelude::*;
use std::sync::Arc;
use std::time::Duration;
use tokio::runtime::Runtime;

use crate::errors::map_sdk_error;

/// Wait for a table to become active.
///
/// Polls the table status until it becomes ACTIVE or times out.
///
/// # Arguments
///
/// * `client` - The DynamoDB client
/// * `runtime` - The Tokio runtime
/// * `table_name` - Name of the table to wait for
/// * `timeout_seconds` - Maximum time to wait (default: 60)
pub fn wait_for_table_active(
    client: &Client,
    runtime: &Arc<Runtime>,
    table_name: &str,
    timeout_seconds: Option<u64>,
) -> PyResult<()> {
    let client = client.clone();
    let table_name = table_name.to_string();
    let timeout = timeout_seconds.unwrap_or(60);

    runtime.block_on(async {
        let start = std::time::Instant::now();
        let poll_interval = Duration::from_millis(500);

        loop {
            if start.elapsed().as_secs() > timeout {
                return Err(PyErr::new::<pyo3::exceptions::PyTimeoutError, _>(format!(
                    "Timeout waiting for table '{}' to become active",
                    table_name
                )));
            }

            let result = client.describe_table().table_name(&table_name).send().await;

            match result {
                Ok(response) => {
                    if let Some(table) = response.table() {
                        if table.table_status() == Some(&TableStatus::Active) {
                            return Ok(());
                        }
                    }
                }
                Err(e) => {
                    // Check if it's ResourceNotFoundException (table still being created)
                    if let Some(service_error) = e.as_service_error() {
                        if !service_error.is_resource_not_found_exception() {
                            return Err(map_sdk_error(e, Some(&table_name)));
                        }
                    } else {
                        return Err(map_sdk_error(e, Some(&table_name)));
                    }
                }
            }

            tokio::time::sleep(poll_interval).await;
        }
    })
}
