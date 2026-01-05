//! Scan operation.

use aws_sdk_dynamodb::types::{AttributeValue, ReturnConsumedCapacity, Select};
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

/// Scan result containing items, pagination info, and metrics (Python types).
pub struct ScanResult {
    pub items: Vec<Py<PyAny>>,
    pub last_evaluated_key: Option<Py<PyAny>>,
    pub metrics: OperationMetrics,
}

/// Raw scan result (before Python conversion).
pub struct RawScanResult {
    pub items: Vec<HashMap<String, AttributeValue>>,
    pub last_evaluated_key: Option<HashMap<String, AttributeValue>>,
    pub metrics: OperationMetrics,
}

/// Prepared scan data (converted from Python).
pub struct PreparedScan {
    pub table: String,
    pub filter_expression: Option<String>,
    pub expression_attribute_names: Option<HashMap<String, String>>,
    pub expression_attribute_values: Option<HashMap<String, AttributeValue>>,
    pub limit: Option<i32>,
    pub exclusive_start_key: Option<HashMap<String, AttributeValue>>,
    pub index_name: Option<String>,
    pub consistent_read: bool,
    pub segment: Option<i32>,
    pub total_segments: Option<i32>,
}

/// Prepare scan by converting Python data to Rust.
#[allow(clippy::too_many_arguments)]
pub fn prepare_scan(
    py: Python<'_>,
    table: &str,
    filter_expression: Option<String>,
    expression_attribute_names: Option<&Bound<'_, PyDict>>,
    expression_attribute_values: Option<&Bound<'_, PyDict>>,
    limit: Option<i32>,
    exclusive_start_key: Option<&Bound<'_, PyDict>>,
    index_name: Option<String>,
    consistent_read: bool,
    segment: Option<i32>,
    total_segments: Option<i32>,
) -> PyResult<PreparedScan> {
    let names = match expression_attribute_names {
        Some(dict) => {
            let mut map = HashMap::new();
            for (k, v) in dict.iter() {
                map.insert(k.extract::<String>()?, v.extract::<String>()?);
            }
            Some(map)
        }
        None => None,
    };

    let values = match expression_attribute_values {
        Some(dict) => Some(py_dict_to_attribute_values(py, dict)?),
        None => None,
    };

    let start_key = match exclusive_start_key {
        Some(dict) => Some(py_dict_to_attribute_values(py, dict)?),
        None => None,
    };

    Ok(PreparedScan {
        table: table.to_string(),
        filter_expression,
        expression_attribute_names: names,
        expression_attribute_values: values,
        limit,
        exclusive_start_key: start_key,
        index_name,
        consistent_read,
        segment,
        total_segments,
    })
}

/// Core async scan operation.
pub async fn execute_scan(
    client: Client,
    prepared: PreparedScan,
) -> Result<
    RawScanResult,
    (
        aws_sdk_dynamodb::error::SdkError<aws_sdk_dynamodb::operation::scan::ScanError>,
        String,
    ),
> {
    let mut request = client
        .scan()
        .table_name(&prepared.table)
        .return_consumed_capacity(ReturnConsumedCapacity::Total);

    if let Some(filter) = prepared.filter_expression {
        request = request.filter_expression(filter);
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

    if let Some(idx) = prepared.index_name {
        request = request.index_name(idx);
    }

    if prepared.consistent_read {
        request = request.consistent_read(true);
    }

    // Parallel scan support
    if let (Some(seg), Some(total)) = (prepared.segment, prepared.total_segments) {
        request = request.segment(seg).total_segments(total);
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

            Ok(RawScanResult {
                items,
                last_evaluated_key: last_key,
                metrics,
            })
        }
        Err(e) => Err((e, prepared.table)),
    }
}

/// Convert raw scan result to Python types.
fn raw_to_py_result(py: Python<'_>, raw: RawScanResult) -> PyResult<ScanResult> {
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

    Ok(ScanResult {
        items,
        last_evaluated_key: last_key,
        metrics: raw.metrics,
    })
}

/// Sync scan - blocks until complete.
#[allow(clippy::too_many_arguments)]
pub fn scan(
    py: Python<'_>,
    client: &Client,
    runtime: &Arc<Runtime>,
    table: &str,
    filter_expression: Option<String>,
    expression_attribute_names: Option<&Bound<'_, PyDict>>,
    expression_attribute_values: Option<&Bound<'_, PyDict>>,
    limit: Option<i32>,
    exclusive_start_key: Option<&Bound<'_, PyDict>>,
    index_name: Option<String>,
    consistent_read: bool,
    segment: Option<i32>,
    total_segments: Option<i32>,
) -> PyResult<ScanResult> {
    let prepared = prepare_scan(
        py,
        table,
        filter_expression,
        expression_attribute_names,
        expression_attribute_values,
        limit,
        exclusive_start_key,
        index_name,
        consistent_read,
        segment,
        total_segments,
    )?;

    let result = runtime.block_on(execute_scan(client.clone(), prepared));

    match result {
        Ok(raw) => raw_to_py_result(py, raw),
        Err((e, tbl)) => Err(map_sdk_error(e, Some(&tbl))),
    }
}

/// Async scan - returns a Python awaitable.
#[allow(clippy::too_many_arguments)]
pub fn async_scan<'py>(
    py: Python<'py>,
    client: Client,
    table: &str,
    filter_expression: Option<String>,
    expression_attribute_names: Option<&Bound<'_, PyDict>>,
    expression_attribute_values: Option<&Bound<'_, PyDict>>,
    limit: Option<i32>,
    exclusive_start_key: Option<&Bound<'_, PyDict>>,
    index_name: Option<String>,
    consistent_read: bool,
    segment: Option<i32>,
    total_segments: Option<i32>,
) -> PyResult<Bound<'py, PyAny>> {
    let prepared = prepare_scan(
        py,
        table,
        filter_expression,
        expression_attribute_names,
        expression_attribute_values,
        limit,
        exclusive_start_key,
        index_name,
        consistent_read,
        segment,
        total_segments,
    )?;

    pyo3_async_runtimes::tokio::future_into_py(py, async move {
        let result = execute_scan(client, prepared).await;

        #[allow(deprecated)]
        Python::with_gil(|py| match result {
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

/// Prepared count data.
pub struct PreparedCount {
    pub table: String,
    pub filter_expression: Option<String>,
    pub expression_attribute_names: Option<HashMap<String, String>>,
    pub expression_attribute_values: Option<HashMap<String, AttributeValue>>,
    pub index_name: Option<String>,
    pub consistent_read: bool,
}

/// Prepare count by converting Python data to Rust.
pub fn prepare_count(
    py: Python<'_>,
    table: &str,
    filter_expression: Option<String>,
    expression_attribute_names: Option<&Bound<'_, PyDict>>,
    expression_attribute_values: Option<&Bound<'_, PyDict>>,
    index_name: Option<String>,
    consistent_read: bool,
) -> PyResult<PreparedCount> {
    let names = match expression_attribute_names {
        Some(dict) => {
            let mut map = HashMap::new();
            for (k, v) in dict.iter() {
                map.insert(k.extract::<String>()?, v.extract::<String>()?);
            }
            Some(map)
        }
        None => None,
    };

    let values = match expression_attribute_values {
        Some(dict) => Some(py_dict_to_attribute_values(py, dict)?),
        None => None,
    };

    Ok(PreparedCount {
        table: table.to_string(),
        filter_expression,
        expression_attribute_names: names,
        expression_attribute_values: values,
        index_name,
        consistent_read,
    })
}

/// Count result with metrics.
pub struct CountResult {
    pub count: i64,
    pub metrics: OperationMetrics,
}

/// Core async count operation (uses scan with SELECT COUNT).
pub async fn execute_count(
    client: Client,
    prepared: PreparedCount,
) -> Result<
    CountResult,
    (
        aws_sdk_dynamodb::error::SdkError<aws_sdk_dynamodb::operation::scan::ScanError>,
        String,
    ),
> {
    let mut total_count: i64 = 0;
    let mut total_duration_ms: f64 = 0.0;
    let mut total_rcu: Option<f64> = None;
    let mut last_key: Option<HashMap<String, AttributeValue>> = None;

    loop {
        let mut request = client
            .scan()
            .table_name(&prepared.table)
            .select(Select::Count)
            .return_consumed_capacity(ReturnConsumedCapacity::Total);

        if let Some(ref filter) = prepared.filter_expression {
            request = request.filter_expression(filter.clone());
        }

        if let Some(ref names) = prepared.expression_attribute_names {
            for (placeholder, attr_name) in names {
                request = request.expression_attribute_names(placeholder, attr_name);
            }
        }

        if let Some(ref values) = prepared.expression_attribute_values {
            for (placeholder, attr_value) in values {
                request = request.expression_attribute_values(placeholder, attr_value.clone());
            }
        }

        if let Some(ref idx) = prepared.index_name {
            request = request.index_name(idx);
        }

        if prepared.consistent_read {
            request = request.consistent_read(true);
        }

        if let Some(ref start_key) = last_key {
            request = request.set_exclusive_start_key(Some(start_key.clone()));
        }

        let start = Instant::now();
        let result = request.send().await;
        let duration_ms = start.elapsed().as_secs_f64() * 1000.0;
        total_duration_ms += duration_ms;

        match result {
            Ok(output) => {
                total_count += output.count() as i64;

                if let Some(consumed) = output.consumed_capacity().and_then(|c| c.capacity_units())
                {
                    total_rcu = Some(total_rcu.unwrap_or(0.0) + consumed);
                }

                last_key = output.last_evaluated_key;
                if last_key.is_none() {
                    break;
                }
            }
            Err(e) => return Err((e, prepared.table)),
        }
    }

    let metrics = OperationMetrics::with_capacity(total_duration_ms, total_rcu, None, None)
        .with_items_count(total_count as usize);

    Ok(CountResult {
        count: total_count,
        metrics,
    })
}

/// Sync count - blocks until complete.
#[allow(clippy::too_many_arguments)]
pub fn count(
    py: Python<'_>,
    client: &Client,
    runtime: &Arc<Runtime>,
    table: &str,
    filter_expression: Option<String>,
    expression_attribute_names: Option<&Bound<'_, PyDict>>,
    expression_attribute_values: Option<&Bound<'_, PyDict>>,
    index_name: Option<String>,
    consistent_read: bool,
) -> PyResult<(i64, OperationMetrics)> {
    let prepared = prepare_count(
        py,
        table,
        filter_expression,
        expression_attribute_names,
        expression_attribute_values,
        index_name,
        consistent_read,
    )?;

    let result = runtime.block_on(execute_count(client.clone(), prepared));

    match result {
        Ok(r) => Ok((r.count, r.metrics)),
        Err((e, tbl)) => Err(map_sdk_error(e, Some(&tbl))),
    }
}

/// Async count - returns a Python awaitable.
#[allow(clippy::too_many_arguments)]
pub fn async_count<'py>(
    py: Python<'py>,
    client: Client,
    table: &str,
    filter_expression: Option<String>,
    expression_attribute_names: Option<&Bound<'_, PyDict>>,
    expression_attribute_values: Option<&Bound<'_, PyDict>>,
    index_name: Option<String>,
    consistent_read: bool,
) -> PyResult<Bound<'py, PyAny>> {
    let prepared = prepare_count(
        py,
        table,
        filter_expression,
        expression_attribute_names,
        expression_attribute_values,
        index_name,
        consistent_read,
    )?;

    pyo3_async_runtimes::tokio::future_into_py(py, async move {
        let result = execute_count(client, prepared).await;

        #[allow(deprecated)]
        Python::with_gil(|py| match result {
            Ok(r) => {
                let py_result = PyDict::new(py);
                py_result.set_item("count", r.count)?;
                py_result.set_item("metrics", r.metrics.into_pyobject(py)?)?;
                Ok(py_result.into_any().unbind())
            }
            Err((e, tbl)) => Err(map_sdk_error(e, Some(&tbl))),
        })
    })
}
