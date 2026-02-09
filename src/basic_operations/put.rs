//! Put item operation.

use aws_sdk_dynamodb::types::{
    AttributeValue, ReturnConsumedCapacity, ReturnValuesOnConditionCheckFailure,
};
use aws_sdk_dynamodb::Client;
use pyo3::prelude::*;
use pyo3::types::PyDict;
use std::collections::HashMap;
use std::sync::Arc;
use std::time::Instant;
use tokio::runtime::Runtime;

use crate::conversions::{extract_string_map, py_dict_to_attribute_values};
use crate::errors::map_sdk_error_with_item;
use crate::metrics::OperationMetrics;

/// Prepared put_item data (converted from Python).
pub struct PreparedPutItem {
    pub table: String,
    pub item: HashMap<String, AttributeValue>,
    pub condition_expression: Option<String>,
    pub expression_attribute_names: Option<HashMap<String, String>>,
    pub expression_attribute_values: Option<HashMap<String, AttributeValue>>,
    pub return_values_on_condition_check_failure: Option<ReturnValuesOnConditionCheckFailure>,
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
    return_values_on_condition_check_failure: bool,
) -> PyResult<PreparedPutItem> {
    let dynamo_item = py_dict_to_attribute_values(py, item)?;
    let names = extract_string_map(expression_attribute_names)?;

    let values = match expression_attribute_values {
        Some(dict) => Some(py_dict_to_attribute_values(py, dict)?),
        None => None,
    };

    let return_on_failure = if return_values_on_condition_check_failure {
        Some(ReturnValuesOnConditionCheckFailure::AllOld)
    } else {
        None
    };

    Ok(PreparedPutItem {
        table: table.to_string(),
        item: dynamo_item,
        condition_expression,
        expression_attribute_names: names,
        expression_attribute_values: values,
        return_values_on_condition_check_failure: return_on_failure,
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
        Option<HashMap<String, AttributeValue>>,
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
    if let Some(return_on_failure) = prepared.return_values_on_condition_check_failure {
        request = request.return_values_on_condition_check_failure(return_on_failure);
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
        Err(e) => {
            // Extract item from ConditionalCheckFailedException if present
            let item = extract_item_from_put_error(&e);
            Err((e, prepared.table, item))
        }
    }
}

/// Extract the item from a ConditionalCheckFailedException.
fn extract_item_from_put_error(
    err: &aws_sdk_dynamodb::error::SdkError<aws_sdk_dynamodb::operation::put_item::PutItemError>,
) -> Option<HashMap<String, AttributeValue>> {
    use aws_sdk_dynamodb::operation::put_item::PutItemError;

    if let aws_sdk_dynamodb::error::SdkError::ServiceError(service_err) = err {
        if let PutItemError::ConditionalCheckFailedException(ccf) = service_err.err() {
            return ccf.item().cloned();
        }
    }
    None
}

/// Sync put_item - blocks until complete.
#[allow(clippy::too_many_arguments)]
pub fn sync_put_item(
    py: Python<'_>,
    client: &Client,
    runtime: &Arc<Runtime>,
    table: &str,
    item: &Bound<'_, PyDict>,
    condition_expression: Option<String>,
    expression_attribute_names: Option<&Bound<'_, PyDict>>,
    expression_attribute_values: Option<&Bound<'_, PyDict>>,
    return_values_on_condition_check_failure: bool,
) -> PyResult<OperationMetrics> {
    let prepared = prepare_put_item(
        py,
        table,
        item,
        condition_expression,
        expression_attribute_names,
        expression_attribute_values,
        return_values_on_condition_check_failure,
    )?;

    let result = py.detach(|| runtime.block_on(execute_put_item(client.clone(), prepared)));

    match result {
        Ok(metrics) => Ok(metrics),
        Err((e, tbl, item)) => Err(map_sdk_error_with_item(py, e, Some(&tbl), item)),
    }
}

/// Async put_item - returns a Python awaitable (default).
#[allow(clippy::too_many_arguments)]
pub fn put_item<'py>(
    py: Python<'py>,
    client: Client,
    table: &str,
    item: &Bound<'_, PyDict>,
    condition_expression: Option<String>,
    expression_attribute_names: Option<&Bound<'_, PyDict>>,
    expression_attribute_values: Option<&Bound<'_, PyDict>>,
    return_values_on_condition_check_failure: bool,
) -> PyResult<Bound<'py, PyAny>> {
    let prepared = prepare_put_item(
        py,
        table,
        item,
        condition_expression,
        expression_attribute_names,
        expression_attribute_values,
        return_values_on_condition_check_failure,
    )?;

    pyo3_async_runtimes::tokio::future_into_py(py, async move {
        let result = execute_put_item(client, prepared).await;
        match result {
            Ok(metrics) => Ok(metrics),
            Err((e, tbl, item)) => {
                Python::attach(|py| Err(map_sdk_error_with_item(py, e, Some(&tbl), item)))
            }
        }
    })
}
