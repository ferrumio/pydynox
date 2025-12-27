//! Batch operations module for DynamoDB.
//!
//! Handles batch write and batch get operations with:
//! - Automatic splitting to respect DynamoDB limits (25 items for write, 100 for get)
//! - Automatic retry of unprocessed items with exponential backoff

use aws_sdk_dynamodb::types::{DeleteRequest, PutRequest, WriteRequest};
use aws_sdk_dynamodb::Client;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use std::collections::HashMap;
use std::sync::Arc;
use tokio::runtime::Runtime;

use crate::basic_operations::py_dict_to_attribute_values;

/// Maximum items per batch write request (DynamoDB limit).
const BATCH_WRITE_MAX_ITEMS: usize = 25;

/// Maximum retry attempts for unprocessed items.
const BATCH_WRITE_MAX_RETRIES: usize = 5;

/// Batch write items to a DynamoDB table.
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
pub fn batch_write(
    py: Python<'_>,
    client: &Client,
    runtime: &Arc<Runtime>,
    table: &str,
    put_items: &Bound<'_, PyList>,
    delete_keys: &Bound<'_, PyList>,
) -> PyResult<()> {
    // Convert put items to WriteRequests
    let mut put_requests: Vec<WriteRequest> = Vec::new();
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
        put_requests.push(WriteRequest::builder().put_request(put_request).build());
    }

    // Convert delete keys to WriteRequests
    let mut delete_requests: Vec<WriteRequest> = Vec::new();
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
        delete_requests.push(
            WriteRequest::builder()
                .delete_request(delete_request)
                .build(),
        );
    }

    // Combine all requests
    let mut all_requests: Vec<WriteRequest> = Vec::new();
    all_requests.extend(put_requests);
    all_requests.extend(delete_requests);

    if all_requests.is_empty() {
        return Ok(());
    }

    let table_name = table.to_string();
    let client = client.clone();

    // Process in batches of 25
    for chunk in all_requests.chunks(BATCH_WRITE_MAX_ITEMS) {
        let mut pending: Vec<WriteRequest> = chunk.to_vec();
        let mut retries = 0;

        while !pending.is_empty() && retries < BATCH_WRITE_MAX_RETRIES {
            let mut request_items = HashMap::new();
            request_items.insert(table_name.clone(), pending.clone());

            let result = runtime.block_on(async {
                client
                    .batch_write_item()
                    .set_request_items(Some(request_items))
                    .send()
                    .await
            });

            match result {
                Ok(output) => {
                    // Check for unprocessed items
                    if let Some(unprocessed) = output.unprocessed_items {
                        if let Some(items) = unprocessed.get(&table_name) {
                            if !items.is_empty() {
                                pending = items.clone();
                                retries += 1;
                                // Exponential backoff
                                let delay = std::time::Duration::from_millis(50 * (1 << retries));
                                std::thread::sleep(delay);
                                continue;
                            }
                        }
                    }
                    // All items processed
                    pending.clear();
                }
                Err(e) => {
                    let err_msg = e.to_string();
                    if err_msg.contains("ResourceNotFoundException")
                        || err_msg.contains("resource not found")
                    {
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                            "Table not found: {}",
                            table
                        )));
                    } else if err_msg.contains("ValidationException") {
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                            "Validation error: {}",
                            err_msg
                        )));
                    } else {
                        return Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!(
                            "Failed to batch write: {}",
                            err_msg
                        )));
                    }
                }
            }
        }

        // If we still have pending items after max retries, fail
        if !pending.is_empty() {
            return Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!(
                "Failed to process {} items after {} retries",
                pending.len(),
                BATCH_WRITE_MAX_RETRIES
            )));
        }
    }

    Ok(())
}
