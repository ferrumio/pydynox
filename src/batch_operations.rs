//! Batch operations module for DynamoDB.
//!
//! Handles batch write and batch get operations with:
//! - Automatic splitting to respect DynamoDB limits (25 items for write, 100 for get)
//! - Automatic retry of unprocessed items with exponential backoff

use aws_sdk_dynamodb::types::{DeleteRequest, KeysAndAttributes, PutRequest, WriteRequest};
use aws_sdk_dynamodb::Client;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use std::collections::HashMap;
use std::sync::Arc;
use tokio::runtime::Runtime;

use crate::basic_operations::{attribute_values_to_py_dict, py_dict_to_attribute_values};
use crate::errors::map_sdk_error;

/// Maximum items per batch write request (DynamoDB limit).
const BATCH_WRITE_MAX_ITEMS: usize = 25;

/// Maximum items per batch get request (DynamoDB limit).
const BATCH_GET_MAX_ITEMS: usize = 100;

/// Maximum retry attempts for unprocessed items.
const BATCH_MAX_RETRIES: usize = 5;

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

        while !pending.is_empty() && retries < BATCH_MAX_RETRIES {
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
                    return Err(map_sdk_error(e, Some(table)));
                }
            }
        }

        // If we still have pending items after max retries, fail
        if !pending.is_empty() {
            return Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!(
                "Failed to process {} items after {} retries",
                pending.len(),
                BATCH_MAX_RETRIES
            )));
        }
    }

    Ok(())
}

/// Batch get items from a DynamoDB table.
///
/// Handles:
/// - Splitting requests to respect the 100-item limit
/// - Retrying unprocessed keys with exponential backoff
/// - Combining results from multiple requests
///
/// # Arguments
///
/// * `py` - Python interpreter reference
/// * `client` - DynamoDB client
/// * `runtime` - Tokio runtime
/// * `table` - Table name
/// * `keys` - List of keys to get (as Python dicts)
///
/// # Returns
///
/// A list of items (as Python dicts) that were found.
pub fn batch_get(
    py: Python<'_>,
    client: &Client,
    runtime: &Arc<Runtime>,
    table: &str,
    keys: &Bound<'_, PyList>,
) -> PyResult<Vec<Py<PyAny>>> {
    use aws_sdk_dynamodb::types::AttributeValue;

    // Convert Python keys to DynamoDB format
    let mut all_keys: Vec<HashMap<String, AttributeValue>> = Vec::new();
    for key in keys.iter() {
        let key_dict = key.cast::<PyDict>()?;
        let dynamo_key = py_dict_to_attribute_values(py, key_dict)?;
        all_keys.push(dynamo_key);
    }

    if all_keys.is_empty() {
        return Ok(Vec::new());
    }

    let table_name = table.to_string();
    let client = client.clone();
    let mut all_results: Vec<Py<PyAny>> = Vec::new();

    // Process in batches of 100
    for chunk in all_keys.chunks(BATCH_GET_MAX_ITEMS) {
        let mut pending: Vec<HashMap<String, AttributeValue>> = chunk.to_vec();
        let mut retries = 0;

        while !pending.is_empty() && retries < BATCH_MAX_RETRIES {
            let keys_and_attrs = KeysAndAttributes::builder()
                .set_keys(Some(pending.clone()))
                .build()
                .map_err(|e| {
                    PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                        "Failed to build keys and attributes: {}",
                        e
                    ))
                })?;

            let mut request_items = HashMap::new();
            request_items.insert(table_name.clone(), keys_and_attrs);

            let result = runtime.block_on(async {
                client
                    .batch_get_item()
                    .set_request_items(Some(request_items))
                    .send()
                    .await
            });

            match result {
                Ok(output) => {
                    // Collect results
                    if let Some(responses) = output.responses {
                        if let Some(items) = responses.get(&table_name) {
                            for item in items {
                                let py_item = attribute_values_to_py_dict(py, item.clone())?;
                                all_results.push(py_item.into_any().unbind());
                            }
                        }
                    }

                    // Check for unprocessed keys
                    if let Some(unprocessed) = output.unprocessed_keys {
                        if let Some(keys_and_attrs) = unprocessed.get(&table_name) {
                            let keys = keys_and_attrs.keys();
                            if !keys.is_empty() {
                                pending = keys.to_vec();
                                retries += 1;
                                // Exponential backoff
                                let delay = std::time::Duration::from_millis(50 * (1 << retries));
                                std::thread::sleep(delay);
                                continue;
                            }
                        }
                    }
                    // All keys processed
                    pending.clear();
                }
                Err(e) => {
                    return Err(map_sdk_error(e, Some(table)));
                }
            }
        }

        // If we still have pending keys after max retries, fail
        if !pending.is_empty() {
            return Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!(
                "Failed to get {} keys after {} retries",
                pending.len(),
                BATCH_MAX_RETRIES
            )));
        }
    }

    Ok(all_results)
}
