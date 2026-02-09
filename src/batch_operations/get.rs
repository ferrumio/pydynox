//! Batch get operations for DynamoDB.

use aws_sdk_dynamodb::types::{AttributeValue, KeysAndAttributes};
use aws_sdk_dynamodb::Client;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use std::collections::HashMap;
use std::sync::Arc;
use tokio::runtime::Runtime;

use crate::conversions::{attribute_values_to_py_dict, py_dict_to_attribute_values};
use crate::errors::map_sdk_error;

/// Maximum items per batch get request (DynamoDB limit).
const BATCH_GET_MAX_ITEMS: usize = 100;

/// Maximum retry attempts for unprocessed items.
const BATCH_MAX_RETRIES: usize = 5;

/// Prepared batch get data (converted from Python before execution).
struct PreparedBatchGet {
    table: String,
    keys: Vec<HashMap<String, AttributeValue>>,
}

/// Prepare batch get - convert Python dicts to Rust types (needs GIL).
fn prepare_batch_get(
    py: Python<'_>,
    table: &str,
    keys: &Bound<'_, PyList>,
) -> PyResult<PreparedBatchGet> {
    let mut all_keys: Vec<HashMap<String, AttributeValue>> = Vec::new();
    for key in keys.iter() {
        let key_dict = key.cast::<PyDict>()?;
        let dynamo_key = py_dict_to_attribute_values(py, key_dict)?;
        all_keys.push(dynamo_key);
    }

    Ok(PreparedBatchGet {
        table: table.to_string(),
        keys: all_keys,
    })
}

/// Raw batch get result (before Python conversion).
struct RawBatchGetResult {
    items: Vec<HashMap<String, AttributeValue>>,
}

/// Execute batch get asynchronously (core logic).
async fn execute_batch_get(
    client: &Client,
    prepared: &PreparedBatchGet,
) -> Result<
    RawBatchGetResult,
    (
        aws_sdk_dynamodb::error::SdkError<
            aws_sdk_dynamodb::operation::batch_get_item::BatchGetItemError,
        >,
        String,
    ),
> {
    if prepared.keys.is_empty() {
        return Ok(RawBatchGetResult { items: Vec::new() });
    }

    let mut all_results: Vec<HashMap<String, AttributeValue>> = Vec::new();

    for chunk in prepared.keys.chunks(BATCH_GET_MAX_ITEMS) {
        let mut pending: Vec<HashMap<String, AttributeValue>> = chunk.to_vec();
        let mut retries = 0;

        while !pending.is_empty() && retries < BATCH_MAX_RETRIES {
            let keys_and_attrs = KeysAndAttributes::builder()
                .set_keys(Some(pending.clone()))
                .build()
                .map_err(|e| {
                    (
                        aws_sdk_dynamodb::error::SdkError::construction_failure(format!(
                            "Failed to build keys and attributes: {}",
                            e
                        )),
                        prepared.table.clone(),
                    )
                })?;

            let mut request_items = HashMap::new();
            request_items.insert(prepared.table.clone(), keys_and_attrs);

            let result = client
                .batch_get_item()
                .set_request_items(Some(request_items))
                .send()
                .await;

            match result {
                Ok(output) => {
                    if let Some(responses) = output.responses {
                        if let Some(items) = responses.get(&prepared.table) {
                            all_results.extend(items.clone());
                        }
                    }

                    if let Some(unprocessed) = output.unprocessed_keys {
                        if let Some(keys_and_attrs) = unprocessed.get(&prepared.table) {
                            let keys = keys_and_attrs.keys();
                            if !keys.is_empty() {
                                pending = keys.to_vec();
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
                    "Failed to get {} keys after {} retries",
                    pending.len(),
                    BATCH_MAX_RETRIES
                )),
                prepared.table.clone(),
            ));
        }
    }

    Ok(RawBatchGetResult { items: all_results })
}

// ========== SYNC (with sync_ prefix) ==========

/// Sync batch get items from a DynamoDB table.
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
pub fn sync_batch_get(
    py: Python<'_>,
    client: &Client,
    runtime: &Arc<Runtime>,
    table: &str,
    keys: &Bound<'_, PyList>,
) -> PyResult<Vec<Py<PyAny>>> {
    let prepared = prepare_batch_get(py, table, keys)?;

    let result = py.detach(|| runtime.block_on(execute_batch_get(client, &prepared)));

    match result {
        Ok(raw) => {
            let mut py_results: Vec<Py<PyAny>> = Vec::new();
            for item in raw.items {
                let py_dict = attribute_values_to_py_dict(py, item)?;
                py_results.push(py_dict.into_any().unbind());
            }
            Ok(py_results)
        }
        Err((e, tbl)) => Err(map_sdk_error(e, Some(&tbl))),
    }
}

// ========== ASYNC (default, no prefix) ==========

/// Async batch get - returns a Python awaitable (default, no prefix).
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
/// * `table` - Table name
/// * `keys` - List of keys to get (as Python dicts)
///
/// # Returns
///
/// A Python awaitable that resolves to a list of items (as Python dicts).
pub fn batch_get<'py>(
    py: Python<'py>,
    client: Client,
    table: &str,
    keys: &Bound<'_, PyList>,
) -> PyResult<Bound<'py, PyAny>> {
    let prepared = prepare_batch_get(py, table, keys)?;

    pyo3_async_runtimes::tokio::future_into_py(py, async move {
        let result = execute_batch_get(&client, &prepared).await;

        Python::attach(|py| match result {
            Ok(raw) => {
                let py_list = PyList::empty(py);
                for item in raw.items {
                    let py_dict = attribute_values_to_py_dict(py, item)?;
                    py_list.append(py_dict)?;
                }
                Ok(py_list.into_any().unbind())
            }
            Err((e, tbl)) => Err(map_sdk_error(e, Some(&tbl))),
        })
    })
}
