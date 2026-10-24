//! Wait for table to become active or to be deleted.

use aws_sdk_dynamodb::Client;
use aws_sdk_dynamodb::types::TableStatus;
use pyo3::prelude::*;
use std::sync::Arc;
use std::time::Duration;
use tokio::runtime::Runtime;

use crate::errors::map_sdk_error;

/// Execute wait_for_table_active asynchronously.
pub async fn execute_wait_for_table_active(
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
                "Timeout waiting for table '{}' to become active",
                table_name
            )));
        }

        let result = client.describe_table().table_name(table_name).send().await;

        match result {
            Ok(response) => {
                if let Some(table) = response.table()
                    && table.table_status() == Some(&TableStatus::Active)
                {
                    return Ok(());
                }
            }
            Err(e) => {
                // Check if it's ResourceNotFoundException (table still being created)
                if let Some(service_error) = e.as_service_error() {
                    if !service_error.is_resource_not_found_exception() {
                        return Err(map_sdk_error(e, Some(table_name)));
                    }
                } else {
                    return Err(map_sdk_error(e, Some(table_name)));
                }
            }
        }

        tokio::time::sleep(poll_interval).await;
    }
}

/// Execute wait_for_table_deleted asynchronously.
///
/// Completes when DynamoDB reports ResourceNotFoundException. Any other error
/// is returned, so a permission failure is never taken as proof of deletion.
pub async fn execute_wait_for_table_deleted(
    client: Client,
    table_name: &str,
    timeout_seconds: Option<u64>,
) -> PyResult<()> {
    let timeout = timeout_seconds.unwrap_or(60);
    let start = std::time::Instant::now();
    let poll_interval = Duration::from_millis(500);

    loop {
        let result = client.describe_table().table_name(table_name).send().await;

        match result {
            Ok(_) => {}
            Err(e) => {
                if e.as_service_error()
                    .is_some_and(|se| se.is_resource_not_found_exception())
                {
                    return Ok(());
                }
                return Err(map_sdk_error(e, Some(table_name)));
            }
        }

        if start.elapsed().as_secs() >= timeout {
            return Err(PyErr::new::<pyo3::exceptions::PyTimeoutError, _>(format!(
                "Timeout waiting for table '{}' to be deleted",
                table_name
            )));
        }

        tokio::time::sleep(poll_interval).await;
    }
}

/// Async wait_for_table_active - returns a Python awaitable.
pub fn wait_for_table_active<'py>(
    py: Python<'py>,
    client: Client,
    table_name: &str,
    timeout_seconds: Option<u64>,
) -> PyResult<Bound<'py, PyAny>> {
    let table_name = table_name.to_string();

    pyo3_async_runtimes::tokio::future_into_py(py, async move {
        execute_wait_for_table_active(client, &table_name, timeout_seconds).await
    })
}

/// Sync wait_for_table_active - blocks until complete.
pub fn sync_wait_for_table_active(
    client: &Client,
    runtime: &Arc<Runtime>,
    table_name: &str,
    timeout_seconds: Option<u64>,
) -> PyResult<()> {
    let client = client.clone();
    let table_name = table_name.to_string();

    runtime.block_on(async {
        execute_wait_for_table_active(client, &table_name, timeout_seconds).await
    })
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

/// Sync wait_for_table_deleted - blocks until complete, without holding the GIL.
pub fn sync_wait_for_table_deleted(
    py: Python<'_>,
    client: &Client,
    runtime: &Arc<Runtime>,
    table_name: &str,
    timeout_seconds: Option<u64>,
) -> PyResult<()> {
    let client = client.clone();
    let table_name = table_name.to_string();

    py.detach(|| {
        runtime.block_on(async {
            execute_wait_for_table_deleted(client, &table_name, timeout_seconds).await
        })
    })
}
