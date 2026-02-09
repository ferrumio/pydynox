//! Get item operation.

use aws_sdk_dynamodb::types::{AttributeValue, ReturnConsumedCapacity};
use aws_sdk_dynamodb::Client;
use pyo3::prelude::*;
use pyo3::types::PyDict;
use std::collections::HashMap;
use std::sync::Arc;
use std::time::Instant;
use tokio::runtime::Runtime;

use crate::conversions::{
    attribute_values_to_py_dict, extract_string_map, py_dict_to_attribute_values,
};
use crate::errors::map_sdk_error;
use crate::metrics::OperationMetrics;

/// Raw result from get_item (before Python conversion).
pub struct RawGetItemResult {
    pub item: Option<HashMap<String, AttributeValue>>,
    pub metrics: OperationMetrics,
}

/// Prepared get_item data (converted from Python).
pub struct PreparedGetItem {
    pub table: String,
    pub key: HashMap<String, AttributeValue>,
    pub consistent_read: bool,
    pub projection_expression: Option<String>,
    pub expression_attribute_names: Option<HashMap<String, String>>,
}

/// Prepare get_item by converting Python data to Rust.
pub fn prepare_get_item(
    py: Python<'_>,
    table: &str,
    key: &Bound<'_, PyDict>,
    consistent_read: bool,
    projection_expression: Option<String>,
    expression_attribute_names: Option<&Bound<'_, PyDict>>,
) -> PyResult<PreparedGetItem> {
    let dynamo_key = py_dict_to_attribute_values(py, key)?;
    let names = extract_string_map(expression_attribute_names)?;

    Ok(PreparedGetItem {
        table: table.to_string(),
        key: dynamo_key,
        consistent_read,
        projection_expression,
        expression_attribute_names: names,
    })
}

/// Core async get_item operation.
/// This is the shared logic used by both sync and async wrappers.
pub async fn execute_get_item(
    client: Client,
    prepared: PreparedGetItem,
) -> Result<
    RawGetItemResult,
    (
        aws_sdk_dynamodb::error::SdkError<aws_sdk_dynamodb::operation::get_item::GetItemError>,
        String,
    ),
> {
    let start = Instant::now();

    let mut request = client
        .get_item()
        .table_name(&prepared.table)
        .set_key(Some(prepared.key))
        .consistent_read(prepared.consistent_read)
        .return_consumed_capacity(ReturnConsumedCapacity::Total);

    if let Some(projection) = prepared.projection_expression {
        request = request.projection_expression(projection);
    }

    if let Some(names) = prepared.expression_attribute_names {
        for (placeholder, attr_name) in names {
            request = request.expression_attribute_names(placeholder, attr_name);
        }
    }

    let result = request.send().await;
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
        Err(e) => Err((e, prepared.table)),
    }
}

/// Sync get_item - blocks until complete.
#[allow(clippy::too_many_arguments)]
pub fn sync_get_item(
    py: Python<'_>,
    client: &Client,
    runtime: &Arc<Runtime>,
    table: &str,
    key: &Bound<'_, PyDict>,
    consistent_read: bool,
    projection_expression: Option<String>,
    expression_attribute_names: Option<&Bound<'_, PyDict>>,
) -> PyResult<(Option<Py<PyAny>>, OperationMetrics)> {
    // Prepare: convert Python -> Rust (needs GIL)
    let prepared = prepare_get_item(
        py,
        table,
        key,
        consistent_read,
        projection_expression,
        expression_attribute_names,
    )?;

    // Execute async operation (releases GIL during I/O)
    let result = py.detach(|| runtime.block_on(execute_get_item(client.clone(), prepared)));

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

/// Async get_item - returns a Python awaitable (default).
#[allow(clippy::too_many_arguments)]
pub fn get_item<'py>(
    py: Python<'py>,
    client: Client,
    table: &str,
    key: &Bound<'_, PyDict>,
    consistent_read: bool,
    projection_expression: Option<String>,
    expression_attribute_names: Option<&Bound<'_, PyDict>>,
) -> PyResult<Bound<'py, PyAny>> {
    // Prepare: convert Python -> Rust (needs GIL, done before async)
    let prepared = prepare_get_item(
        py,
        table,
        key,
        consistent_read,
        projection_expression,
        expression_attribute_names,
    )?;

    // Return a Python awaitable
    pyo3_async_runtimes::tokio::future_into_py(py, async move {
        let result = execute_get_item(client, prepared).await;

        // Convert result back to Python (needs GIL)
        Python::attach(|py| match result {
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
