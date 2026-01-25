//! Table deletion operation.

use aws_sdk_dynamodb::Client;
use pyo3::prelude::*;
use std::sync::Arc;
use tokio::runtime::Runtime;

use crate::errors::map_sdk_error;

/// Execute delete table asynchronously.
pub async fn execute_delete_table(client: Client, table_name: String) -> PyResult<()> {
    client
        .delete_table()
        .table_name(&table_name)
        .send()
        .await
        .map_err(|e| map_sdk_error(e, Some(&table_name)))?;

    Ok(())
}

/// Async delete_table - returns a Python awaitable.
pub fn delete_table<'py>(
    py: Python<'py>,
    client: Client,
    table_name: &str,
) -> PyResult<Bound<'py, PyAny>> {
    let table_name = table_name.to_string();

    pyo3_async_runtimes::tokio::future_into_py(py, async move {
        execute_delete_table(client, table_name).await
    })
}

/// Sync delete_table - blocks until complete.
pub fn sync_delete_table(
    client: &Client,
    runtime: &Arc<Runtime>,
    table_name: &str,
) -> PyResult<()> {
    let client = client.clone();
    let table_name = table_name.to_string();

    runtime.block_on(async { execute_delete_table(client, table_name).await })
}
