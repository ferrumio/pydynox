//! Get item operation.

use aws_sdk_dynamodb::types::{AttributeValue, ReturnConsumedCapacity};
use aws_sdk_dynamodb::Client;
use pyo3::prelude::*;
use pyo3::types::PyDict;
use std::collections::HashMap;
use std::sync::Arc;
use std::time::Instant;
use tokio::runtime::Runtime;

use crate::conversions::{attribute_values_to_py_dict, py_dict_to_attribute_values};
use crate::errors::map_sdk_error;
use crate::metrics::OperationMetrics;

/// Raw result from get_item (before Python conversion).
pub struct RawGetItemResult {
    pub item: Option<HashMap<String, AttributeValue>>,
    pub metrics: OperationMetrics,
}

/// Core async get_item operation.
/// This is the shared logic used by both sync and async wrappers.
pub async fn execute_get_item(
    client: Client,
    table: String,
    key: HashMap<String, AttributeValue>,
    consistent_read: bool,
) -> Result<
    RawGetItemResult,
    (
        aws_sdk_dynamodb::error::SdkError<aws_sdk_dynamodb::operation::get_item::GetItemError>,
        String,
    ),
> {
    let start = Instant::now();
    let result = client
        .get_item()
        .table_name(&table)
        .set_key(Some(key))
        .consistent_read(consistent_read)
        .return_consumed_capacity(ReturnConsumedCapacity::Total)
        .send()
        .await;
    let duration_ms = start.elapsed().as_secs_f64() * 1000.0;

    match result {
        Ok(output) => {
            let consumed_rcu = output.consumed_capacity().and_then(|c| c.capacity_units());
            let metrics = OperationMetrics::with_capacity(duration_ms, consumed_rcu, None, None);
            Ok(RawGetItemResult {
                item: output.item,
                metrics,
            })
        }
        Err(e) => Err((e, table)),
    }
}

/// Sync get_item - blocks until complete.
pub fn get_item(
    py: Python<'_>,
    client: &Client,
    runtime: &Arc<Runtime>,
    table: &str,
    key: &Bound<'_, PyDict>,
    consistent_read: bool,
) -> PyResult<(Option<Py<PyAny>>, OperationMetrics)> {
    // Convert Python -> Rust (needs GIL)
    let dynamo_key = py_dict_to_attribute_values(py, key)?;

    // Execute async operation (releases GIL during I/O)
    let result = runtime.block_on(execute_get_item(
        client.clone(),
        table.to_string(),
        dynamo_key,
        consistent_read,
    ));

    // Convert result back to Python (needs GIL)
    match result {
        Ok(raw) => {
            if let Some(item) = raw.item {
                let py_dict = attribute_values_to_py_dict(py, item)?;
                Ok((Some(py_dict.into_any().unbind()), raw.metrics))
            } else {
                Ok((None, raw.metrics))
            }
        }
        Err((e, tbl)) => Err(map_sdk_error(e, Some(&tbl))),
    }
}

/// Async get_item - returns a Python awaitable.
pub fn async_get_item<'py>(
    py: Python<'py>,
    client: Client,
    table: String,
    key: &Bound<'_, PyDict>,
    consistent_read: bool,
) -> PyResult<Bound<'py, PyAny>> {
    // Convert Python -> Rust (needs GIL, done before async)
    let dynamo_key = py_dict_to_attribute_values(py, key)?;

    // Return a Python awaitable
    pyo3_async_runtimes::tokio::future_into_py(py, async move {
        let result = execute_get_item(client, table, dynamo_key, consistent_read).await;

        // Convert result back to Python (needs GIL)
        #[allow(deprecated)]
        Python::with_gil(|py| match result {
            Ok(raw) => {
                let py_result = PyDict::new(py);
                if let Some(item) = raw.item {
                    let py_dict = attribute_values_to_py_dict(py, item)?;
                    py_result.set_item("item", py_dict)?;
                } else {
                    py_result.set_item("item", py.None())?;
                }
                py_result.set_item("metrics", raw.metrics.into_pyobject(py)?)?;
                Ok(py_result.into_any().unbind())
            }
            Err((e, tbl)) => Err(map_sdk_error(e, Some(&tbl))),
        })
    })
}
