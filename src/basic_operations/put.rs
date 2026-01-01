//! Put item operation.

use aws_sdk_dynamodb::types::{AttributeValue, ReturnConsumedCapacity};
use aws_sdk_dynamodb::Client;
use pyo3::prelude::*;
use pyo3::types::PyDict;
use std::collections::HashMap;
use std::sync::Arc;
use std::time::Instant;
use tokio::runtime::Runtime;

use crate::conversions::py_dict_to_attribute_values;
use crate::errors::map_sdk_error;
use crate::metrics::OperationMetrics;

/// Prepared put_item data (converted from Python).
pub struct PreparedPutItem {
    pub table: String,
    pub item: HashMap<String, AttributeValue>,
    pub condition_expression: Option<String>,
    pub expression_attribute_names: Option<HashMap<String, String>>,
    pub expression_attribute_values: Option<HashMap<String, AttributeValue>>,
}

/// Prepare put_item by converting Python data to Rust.
#[allow(clippy::too_many_arguments)]
pub fn prepare_put_item(
    py: Python<'_>,
    table: &str,
    item: &Bound<'_, PyDict>,
    condition_expression: Option<String>,
    expression_attribute_names: Option<&Bound<'_, PyDict>>,
    expression_attribute_values: Option<&Bound<'_, PyDict>>,
) -> PyResult<PreparedPutItem> {
    let dynamo_item = py_dict_to_attribute_values(py, item)?;

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

    Ok(PreparedPutItem {
        table: table.to_string(),
        item: dynamo_item,
        condition_expression,
        expression_attribute_names: names,
        expression_attribute_values: values,
    })
}

/// Core async put_item operation.
pub async fn execute_put_item(
    client: Client,
    prepared: PreparedPutItem,
) -> Result<
    OperationMetrics,
    (
        aws_sdk_dynamodb::error::SdkError<aws_sdk_dynamodb::operation::put_item::PutItemError>,
        String,
    ),
> {
    let mut request = client
        .put_item()
        .table_name(&prepared.table)
        .set_item(Some(prepared.item))
        .return_consumed_capacity(ReturnConsumedCapacity::Total);

    if let Some(condition) = prepared.condition_expression {
        request = request.condition_expression(condition);
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

    let start = Instant::now();
    let result = request.send().await;
    let duration_ms = start.elapsed().as_secs_f64() * 1000.0;

    match result {
        Ok(output) => {
            let consumed_wcu = output.consumed_capacity().and_then(|c| c.capacity_units());
            Ok(OperationMetrics::with_capacity(
                duration_ms,
                None,
                consumed_wcu,
                None,
            ))
        }
        Err(e) => Err((e, prepared.table)),
    }
}

/// Sync put_item - blocks until complete.
#[allow(clippy::too_many_arguments)]
pub fn put_item(
    py: Python<'_>,
    client: &Client,
    runtime: &Arc<Runtime>,
    table: &str,
    item: &Bound<'_, PyDict>,
    condition_expression: Option<String>,
    expression_attribute_names: Option<&Bound<'_, PyDict>>,
    expression_attribute_values: Option<&Bound<'_, PyDict>>,
) -> PyResult<OperationMetrics> {
    let prepared = prepare_put_item(
        py,
        table,
        item,
        condition_expression,
        expression_attribute_names,
        expression_attribute_values,
    )?;

    let result = runtime.block_on(execute_put_item(client.clone(), prepared));

    match result {
        Ok(metrics) => Ok(metrics),
        Err((e, tbl)) => Err(map_sdk_error(e, Some(&tbl))),
    }
}

/// Async put_item - returns a Python awaitable.
#[allow(clippy::too_many_arguments)]
pub fn async_put_item<'py>(
    py: Python<'py>,
    client: Client,
    table: &str,
    item: &Bound<'_, PyDict>,
    condition_expression: Option<String>,
    expression_attribute_names: Option<&Bound<'_, PyDict>>,
    expression_attribute_values: Option<&Bound<'_, PyDict>>,
) -> PyResult<Bound<'py, PyAny>> {
    let prepared = prepare_put_item(
        py,
        table,
        item,
        condition_expression,
        expression_attribute_names,
        expression_attribute_values,
    )?;

    pyo3_async_runtimes::tokio::future_into_py(py, async move {
        let result = execute_put_item(client, prepared).await;
        match result {
            Ok(metrics) => Ok(metrics),
            Err((e, tbl)) => Err(map_sdk_error(e, Some(&tbl))),
        }
    })
}
