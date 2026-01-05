//! Table deletion operation.

use aws_sdk_dynamodb::Client;
use pyo3::prelude::*;
use std::sync::Arc;
use tokio::runtime::Runtime;

use crate::errors::map_sdk_error;

/// Delete a table.
///
/// # Arguments
///
/// * `client` - The DynamoDB client
/// * `runtime` - The Tokio runtime
/// * `table_name` - Name of the table to delete
pub fn delete_table(client: &Client, runtime: &Arc<Runtime>, table_name: &str) -> PyResult<()> {
    let client = client.clone();
    let table_name = table_name.to_string();

    runtime.block_on(async {
        client
            .delete_table()
            .table_name(&table_name)
            .send()
            .await
            .map_err(|e| map_sdk_error(e, Some(&table_name)))?;

        Ok(())
    })
}
