//! Table deletion operation.

use aws_sdk_dynamodb::Client;
use pyo3::prelude::*;
use std::sync::Arc;
use tokio::runtime::Runtime;

use super::wait::execute_wait_for_table_deleted;
use crate::errors::map_sdk_error;

/// Execute delete table asynchronously.
///
/// When `wait` is true, polls until the table no longer exists.
pub async fn execute_delete_table(
    client: Client,
    table_name: String,
    wait: bool,
    timeout_seconds: Option<u64>,
) -> PyResult<()> {
    client
        .delete_table()
        .table_name(&table_name)
        .send()
        .await
        .map_err(|e| map_sdk_error(e, Some(&table_name)))?;

    if wait {
        execute_wait_for_table_deleted(client, &table_name, timeout_seconds).await?;
    }

    Ok(())
}

/// Async delete_table - returns a Python awaitable.
pub fn delete_table<'py>(
    py: Python<'py>,
    client: Client,
    table_name: &str,
    wait: bool,
    timeout_seconds: Option<u64>,
) -> PyResult<Bound<'py, PyAny>> {
    let table_name = table_name.to_string();

    pyo3_async_runtimes::tokio::future_into_py(py, async move {
        execute_delete_table(client, table_name, wait, timeout_seconds).await
    })
}

/// Sync delete_table - blocks until complete, without holding the GIL.
pub fn sync_delete_table(
    py: Python<'_>,
    client: &Client,
    runtime: &Arc<Runtime>,
    table_name: &str,
    wait: bool,
    timeout_seconds: Option<u64>,
) -> PyResult<()> {
    let client = client.clone();
    let table_name = table_name.to_string();

    py.detach(|| {
        runtime.block_on(async {
            execute_delete_table(client, table_name, wait, timeout_seconds).await
        })
    })
}
