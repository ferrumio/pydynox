//! Delete item operation.

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

/// Prepared delete_item data.
pub struct PreparedDeleteItem {
    pub table: String,
    pub key: HashMap<String, AttributeValue>,
    pub condition_expression: Option<String>,
    pub expression_attribute_names: Option<HashMap<String, String>>,
    pub expression_attribute_values: Option<HashMap<String, AttributeValue>>,
    pub return_values_on_condition_check_failure: Option<ReturnValuesOnConditionCheckFailure>,
}

/// Prepare delete_item by converting Python data to Rust.
#[allow(clippy::too_many_arguments)]
pub fn prepare_delete_item(
    py: Python<'_>,
    table: &str,
    key: &Bound<'_, PyDict>,
    condition_expression: Option<String>,
    expression_attribute_names: Option<&Bound<'_, PyDict>>,
    expression_attribute_values: Option<&Bound<'_, PyDict>>,
    return_values_on_condition_check_failure: bool,
) -> PyResult<PreparedDeleteItem> {
    let dynamo_key = py_dict_to_attribute_values(py, key)?;
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

    Ok(PreparedDeleteItem {
        table: table.to_string(),
        key: dynamo_key,
        condition_expression,
        expression_attribute_names: names,
        expression_attribute_values: values,
        return_values_on_condition_check_failure: return_on_failure,
    })
}

/// Core async delete_item operation.
pub async fn execute_delete_item(
    client: Client,
    prepared: PreparedDeleteItem,
) -> Result<
    OperationMetrics,
    (
        aws_sdk_dynamodb::error::SdkError<
            aws_sdk_dynamodb::operation::delete_item::DeleteItemError,
        >,
        String,
        Option<HashMap<String, AttributeValue>>,
    ),
> {
    let mut request = client
        .delete_item()
        .table_name(&prepared.table)
        .set_key(Some(prepared.key))
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
            let item = extract_item_from_delete_error(&e);
            Err((e, prepared.table, item))
        }
    }
}

/// Extract the item from a ConditionalCheckFailedException.
fn extract_item_from_delete_error(
    err: &aws_sdk_dynamodb::error::SdkError<
        aws_sdk_dynamodb::operation::delete_item::DeleteItemError,
    >,
) -> Option<HashMap<String, AttributeValue>> {
    use aws_sdk_dynamodb::operation::delete_item::DeleteItemError;

    if let aws_sdk_dynamodb::error::SdkError::ServiceError(service_err) = err {
        if let DeleteItemError::ConditionalCheckFailedException(ccf) = service_err.err() {
            return ccf.item().cloned();
        }
    }
    None
}

/// Sync delete_item - blocks until complete.
#[allow(clippy::too_many_arguments)]
pub fn sync_delete_item(
    py: Python<'_>,
    client: &Client,
    runtime: &Arc<Runtime>,
    table: &str,
    key: &Bound<'_, PyDict>,
    condition_expression: Option<String>,
    expression_attribute_names: Option<&Bound<'_, PyDict>>,
    expression_attribute_values: Option<&Bound<'_, PyDict>>,
    return_values_on_condition_check_failure: bool,
) -> PyResult<OperationMetrics> {
    let prepared = prepare_delete_item(
        py,
        table,
        key,
        condition_expression,
        expression_attribute_names,
        expression_attribute_values,
        return_values_on_condition_check_failure,
    )?;

    let result = runtime.block_on(execute_delete_item(client.clone(), prepared));

    match result {
        Ok(metrics) => Ok(metrics),
        Err((e, tbl, item)) => Err(map_sdk_error_with_item(py, e, Some(&tbl), item)),
    }
}

/// Async delete_item - returns a Python awaitable (default).
#[allow(clippy::too_many_arguments)]
pub fn delete_item<'py>(
    py: Python<'py>,
    client: Client,
    table: &str,
    key: &Bound<'_, PyDict>,
    condition_expression: Option<String>,
    expression_attribute_names: Option<&Bound<'_, PyDict>>,
    expression_attribute_values: Option<&Bound<'_, PyDict>>,
    return_values_on_condition_check_failure: bool,
) -> PyResult<Bound<'py, PyAny>> {
    let prepared = prepare_delete_item(
        py,
        table,
        key,
        condition_expression,
        expression_attribute_names,
        expression_attribute_values,
        return_values_on_condition_check_failure,
    )?;

    pyo3_async_runtimes::tokio::future_into_py(py, async move {
        let result = execute_delete_item(client, prepared).await;
        match result {
            Ok(metrics) => Ok(metrics),
            Err((e, tbl, item)) => {
                Python::attach(|py| Err(map_sdk_error_with_item(py, e, Some(&tbl), item)))
            }
        }
    })
}
