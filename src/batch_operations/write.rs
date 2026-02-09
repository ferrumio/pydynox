//! Batch write operations for DynamoDB.

use aws_sdk_dynamodb::types::{DeleteRequest, PutRequest, WriteRequest};
use aws_sdk_dynamodb::Client;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use std::collections::HashMap;
use std::sync::Arc;
use tokio::runtime::Runtime;

use crate::conversions::py_dict_to_attribute_values;
use crate::errors::map_sdk_error;

/// Maximum items per batch write request (DynamoDB limit).
const BATCH_WRITE_MAX_ITEMS: usize = 25;

/// Maximum retry attempts for unprocessed items.
const BATCH_MAX_RETRIES: usize = 5;

/// Prepared batch write data (converted from Python before execution).
struct PreparedBatchWrite {
    table: String,
    requests: Vec<WriteRequest>,
}

/// Prepare batch write - convert Python dicts to Rust types (needs GIL).
fn prepare_batch_write(
    py: Python<'_>,
    table: &str,
    put_items: &Bound<'_, PyList>,
    delete_keys: &Bound<'_, PyList>,
) -> PyResult<PreparedBatchWrite> {
    let mut requests: Vec<WriteRequest> = Vec::new();

    // Build put requests
    for item in put_items.iter() {
        let item_dict = item.cast::<PyDict>()?;
        let dynamo_item = py_dict_to_attribute_values(py, item_dict)?;
        let put_request = PutRequest::builder()
            .set_item(Some(dynamo_item))
            .build()
            .map_err(|e| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                    "Failed to build put request: {}",
                    e
                ))
            })?;
        requests.push(WriteRequest::builder().put_request(put_request).build());
    }

    // Build delete requests
    for key in delete_keys.iter() {
        let key_dict = key.cast::<PyDict>()?;
        let dynamo_key = py_dict_to_attribute_values(py, key_dict)?;
        let delete_request = DeleteRequest::builder()
            .set_key(Some(dynamo_key))
            .build()
            .map_err(|e| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                    "Failed to build delete request: {}",
                    e
                ))
            })?;
        requests.push(
            WriteRequest::builder()
                .delete_request(delete_request)
                .build(),
        );
    }

    Ok(PreparedBatchWrite {
        table: table.to_string(),
        requests,
    })
}

/// Execute batch write asynchronously (core logic).
async fn execute_batch_write(
    client: &Client,
    prepared: &PreparedBatchWrite,
) -> Result<
    (),
    (
        aws_sdk_dynamodb::error::SdkError<
            aws_sdk_dynamodb::operation::batch_write_item::BatchWriteItemError,
        >,
        String,
    ),
> {
    if prepared.requests.is_empty() {
        return Ok(());
    }

    for chunk in prepared.requests.chunks(BATCH_WRITE_MAX_ITEMS) {
        let mut pending: Vec<WriteRequest> = chunk.to_vec();
        let mut retries = 0;

        while !pending.is_empty() && retries < BATCH_MAX_RETRIES {
            let mut request_items = HashMap::new();
            request_items.insert(prepared.table.clone(), pending.clone());

            let result = client
                .batch_write_item()
                .set_request_items(Some(request_items))
                .send()
                .await;

            match result {
                Ok(output) => {
                    if let Some(unprocessed) = output.unprocessed_items {
                        if let Some(items) = unprocessed.get(&prepared.table) {
                            if !items.is_empty() {
                                pending = items.clone();
                                retries += 1;
                                let delay = std::time::Duration::from_millis(50 * (1 << retries));
                                tokio::time::sleep(delay).await;
                                continue;
                            }
                        }
                    }
                    pending.clear();
                }
                Err(e) => {
                    return Err((e, prepared.table.clone()));
                }
            }
        }

        if !pending.is_empty() {
            return Err((
                aws_sdk_dynamodb::error::SdkError::construction_failure(format!(
                    "Failed to process {} items after {} retries",
                    pending.len(),
                    BATCH_MAX_RETRIES
                )),
                prepared.table.clone(),
            ));
        }
    }

    Ok(())
}

// ========== SYNC (with sync_ prefix) ==========

/// Sync batch write items to a DynamoDB table.
///
/// Handles:
/// - Splitting requests to respect the 25-item limit
/// - Retrying unprocessed items with exponential backoff
///
/// # Arguments
///
/// * `py` - Python interpreter reference
/// * `client` - DynamoDB client
/// * `runtime` - Tokio runtime
/// * `table` - Table name
/// * `put_items` - List of items to put (as Python dicts)
/// * `delete_keys` - List of keys to delete (as Python dicts)
///
/// # Returns
///
/// Ok(()) on success, or an error if the operation fails.
pub fn sync_batch_write(
    py: Python<'_>,
    client: &Client,
    runtime: &Arc<Runtime>,
    table: &str,
    put_items: &Bound<'_, PyList>,
    delete_keys: &Bound<'_, PyList>,
) -> PyResult<()> {
    let prepared = prepare_batch_write(py, table, put_items, delete_keys)?;

    let result = py.detach(|| runtime.block_on(execute_batch_write(client, &prepared)));

    match result {
        Ok(()) => Ok(()),
        Err((e, tbl)) => Err(map_sdk_error(e, Some(&tbl))),
    }
}

// ========== ASYNC (default, no prefix) ==========

/// Async batch write - returns a Python awaitable (default, no prefix).
///
/// Handles:
/// - Splitting requests to respect the 25-item limit
/// - Retrying unprocessed items with exponential backoff
///
/// # Arguments
///
/// * `py` - Python interpreter reference
/// * `client` - DynamoDB client
/// * `table` - Table name
/// * `put_items` - List of items to put (as Python dicts)
/// * `delete_keys` - List of keys to delete (as Python dicts)
///
/// # Returns
///
/// A Python awaitable that resolves to () on success.
pub fn batch_write<'py>(
    py: Python<'py>,
    client: Client,
    table: &str,
    put_items: &Bound<'_, PyList>,
    delete_keys: &Bound<'_, PyList>,
) -> PyResult<Bound<'py, PyAny>> {
    let prepared = prepare_batch_write(py, table, put_items, delete_keys)?;

    pyo3_async_runtimes::tokio::future_into_py(py, async move {
        let result = execute_batch_write(&client, &prepared).await;

        match result {
            Ok(()) => Ok(()),
            Err((e, tbl)) => Err(map_sdk_error(e, Some(&tbl))),
        }
    })
}
