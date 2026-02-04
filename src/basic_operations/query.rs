//! Query operation.

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

/// Query result containing items, pagination info, and metrics (Python types).
pub struct QueryResult {
    pub items: Vec<Py<PyAny>>,
    pub last_evaluated_key: Option<Py<PyAny>>,
    pub metrics: OperationMetrics,
}

/// Raw query result (before Python conversion).
pub struct RawQueryResult {
    pub items: Vec<HashMap<String, AttributeValue>>,
    pub last_evaluated_key: Option<HashMap<String, AttributeValue>>,
    pub metrics: OperationMetrics,
}

/// Prepared query data (converted from Python).
pub struct PreparedQuery {
    pub table: String,
    pub key_condition_expression: String,
    pub filter_expression: Option<String>,
    pub projection_expression: Option<String>,
    pub expression_attribute_names: Option<HashMap<String, String>>,
    pub expression_attribute_values: Option<HashMap<String, AttributeValue>>,
    pub limit: Option<i32>,
    pub exclusive_start_key: Option<HashMap<String, AttributeValue>>,
    pub scan_index_forward: Option<bool>,
    pub index_name: Option<String>,
    pub consistent_read: bool,
}

/// Prepare query by converting Python data to Rust.
#[allow(clippy::too_many_arguments)]
pub fn prepare_query(
    py: Python<'_>,
    table: &str,
    key_condition_expression: &str,
    filter_expression: Option<String>,
    projection_expression: Option<String>,
    expression_attribute_names: Option<&Bound<'_, PyDict>>,
    expression_attribute_values: Option<&Bound<'_, PyDict>>,
    limit: Option<i32>,
    exclusive_start_key: Option<&Bound<'_, PyDict>>,
    scan_index_forward: Option<bool>,
    index_name: Option<String>,
    consistent_read: bool,
) -> PyResult<PreparedQuery> {
    let names = extract_string_map(expression_attribute_names)?;

    let values = match expression_attribute_values {
        Some(dict) => Some(py_dict_to_attribute_values(py, dict)?),
        None => None,
    };

    let start_key = match exclusive_start_key {
        Some(dict) => Some(py_dict_to_attribute_values(py, dict)?),
        None => None,
    };

    Ok(PreparedQuery {
        table: table.to_string(),
        key_condition_expression: key_condition_expression.to_string(),
        filter_expression,
        projection_expression,
        expression_attribute_names: names,
        expression_attribute_values: values,
        limit,
        exclusive_start_key: start_key,
        scan_index_forward,
        index_name,
        consistent_read,
    })
}

/// Core async query operation.
pub async fn execute_query(
    client: Client,
    prepared: PreparedQuery,
) -> Result<
    RawQueryResult,
    (
        aws_sdk_dynamodb::error::SdkError<aws_sdk_dynamodb::operation::query::QueryError>,
        String,
    ),
> {
    let mut request = client
        .query()
        .table_name(&prepared.table)
        .key_condition_expression(prepared.key_condition_expression)
        .return_consumed_capacity(ReturnConsumedCapacity::Total);

    if let Some(filter) = prepared.filter_expression {
        request = request.filter_expression(filter);
    }

    if let Some(projection) = prepared.projection_expression {
        request = request.projection_expression(projection);
    }

    if let Some(names) = prepared.expression_attribute_names {
        for (placeholder, attr_name) in names {
            request = request.expression_attribute_names(placeholder, attr_name);
        }
    }

    if let Some(values) = prepared.expression_attribute_values {
        for (placeholder, attr_value) in values {
            request = request.expression_attribute_values(placeholder, attr_value);
        }
    }

    if let Some(n) = prepared.limit {
        request = request.limit(n);
    }

    if let Some(start_key) = prepared.exclusive_start_key {
        request = request.set_exclusive_start_key(Some(start_key));
    }

    if let Some(forward) = prepared.scan_index_forward {
        request = request.scan_index_forward(forward);
    }

    if let Some(idx) = prepared.index_name {
        request = request.index_name(idx);
    }

    if prepared.consistent_read {
        request = request.consistent_read(true);
    }

    let start = Instant::now();
    let result = request.send().await;
    let duration_ms = start.elapsed().as_secs_f64() * 1000.0;

    match result {
        Ok(output) => {
            let items_count = output.items.as_ref().map(|i| i.len()).unwrap_or(0);
            let scanned_count = output.scanned_count();
            let consumed_rcu = output.consumed_capacity().and_then(|c| c.capacity_units());

            let items = output.items.unwrap_or_default();
            let last_key = output.last_evaluated_key;

            let metrics = OperationMetrics::with_capacity(duration_ms, consumed_rcu, None, None)
                .with_items_count(items_count)
                .with_scanned_count(scanned_count as usize);

            Ok(RawQueryResult {
                items,
                last_evaluated_key: last_key,
                metrics,
            })
        }
        Err(e) => Err((e, prepared.table)),
    }
}

/// Convert raw query result to Python types.
fn raw_to_py_result(py: Python<'_>, raw: RawQueryResult) -> PyResult<QueryResult> {
    let mut items = Vec::new();
    for item in raw.items {
        let py_dict = attribute_values_to_py_dict(py, item)?;
        items.push(py_dict.into_any().unbind());
    }

    let last_key = if let Some(lek) = raw.last_evaluated_key {
        let py_dict = attribute_values_to_py_dict(py, lek)?;
        Some(py_dict.into_any().unbind())
    } else {
        None
    };

    Ok(QueryResult {
        items,
        last_evaluated_key: last_key,
        metrics: raw.metrics,
    })
}

/// Sync query - blocks until complete.
#[allow(clippy::too_many_arguments)]
pub fn sync_query(
    py: Python<'_>,
    client: &Client,
    runtime: &Arc<Runtime>,
    table: &str,
    key_condition_expression: &str,
    filter_expression: Option<String>,
    projection_expression: Option<String>,
    expression_attribute_names: Option<&Bound<'_, PyDict>>,
    expression_attribute_values: Option<&Bound<'_, PyDict>>,
    limit: Option<i32>,
    exclusive_start_key: Option<&Bound<'_, PyDict>>,
    scan_index_forward: Option<bool>,
    index_name: Option<String>,
    consistent_read: bool,
) -> PyResult<QueryResult> {
    let prepared = prepare_query(
        py,
        table,
        key_condition_expression,
        filter_expression,
        projection_expression,
        expression_attribute_names,
        expression_attribute_values,
        limit,
        exclusive_start_key,
        scan_index_forward,
        index_name,
        consistent_read,
    )?;

    let result = runtime.block_on(execute_query(client.clone(), prepared));

    match result {
        Ok(raw) => raw_to_py_result(py, raw),
        Err((e, tbl)) => Err(map_sdk_error(e, Some(&tbl))),
    }
}

/// Async query - returns a Python awaitable (default).
#[allow(clippy::too_many_arguments)]
pub fn query<'py>(
    py: Python<'py>,
    client: Client,
    table: &str,
    key_condition_expression: &str,
    filter_expression: Option<String>,
    projection_expression: Option<String>,
    expression_attribute_names: Option<&Bound<'_, PyDict>>,
    expression_attribute_values: Option<&Bound<'_, PyDict>>,
    limit: Option<i32>,
    exclusive_start_key: Option<&Bound<'_, PyDict>>,
    scan_index_forward: Option<bool>,
    index_name: Option<String>,
    consistent_read: bool,
) -> PyResult<Bound<'py, PyAny>> {
    let prepared = prepare_query(
        py,
        table,
        key_condition_expression,
        filter_expression,
        projection_expression,
        expression_attribute_names,
        expression_attribute_values,
        limit,
        exclusive_start_key,
        scan_index_forward,
        index_name,
        consistent_read,
    )?;

    pyo3_async_runtimes::tokio::future_into_py(py, async move {
        let result = execute_query(client, prepared).await;

        Python::attach(|py| match result {
            Ok(raw) => {
                let py_result = PyDict::new(py);

                let mut items = Vec::new();
                for item in raw.items {
                    let py_dict = attribute_values_to_py_dict(py, item)?;
                    items.push(py_dict.into_any().unbind());
                }
                py_result.set_item("items", items)?;

                if let Some(lek) = raw.last_evaluated_key {
                    let py_dict = attribute_values_to_py_dict(py, lek)?;
                    py_result.set_item("last_evaluated_key", py_dict)?;
                } else {
                    py_result.set_item("last_evaluated_key", py.None())?;
                }

                py_result.set_item("metrics", raw.metrics.into_pyobject(py)?)?;
                Ok(py_result.into_any().unbind())
            }
            Err((e, tbl)) => Err(map_sdk_error(e, Some(&tbl))),
        })
    })
}
