//! Update item operation.

use aws_sdk_dynamodb::Client;
use aws_sdk_dynamodb::types::{
    AttributeValue, ReturnConsumedCapacity, ReturnValue, ReturnValuesOnConditionCheckFailure,
};
use pyo3::prelude::*;
use pyo3::types::PyDict;
use std::collections::HashMap;
use std::sync::Arc;
use std::time::Instant;
use tokio::runtime::Runtime;

use crate::conversions::{
    attribute_values_to_py_dict, py_dict_to_attribute_values, py_to_attribute_value_direct,
};
use crate::errors::map_sdk_error_with_item;
use crate::metrics::OperationMetrics;

/// Prepared update_item data (converted from Python).
pub struct PreparedUpdateItem {
    pub table: String,
    pub key: HashMap<String, AttributeValue>,
    pub update_expression: String,
    pub condition_expression: Option<String>,
    pub expression_attribute_names: HashMap<String, String>,
    pub expression_attribute_values: HashMap<String, AttributeValue>,
    pub return_values_on_condition_check_failure: Option<ReturnValuesOnConditionCheckFailure>,
    pub return_values: Option<ReturnValue>,
}

/// Convert a Python string to a DynamoDB ReturnValue enum.
fn parse_return_values(value: &str) -> PyResult<ReturnValue> {
    match value {
        "NONE" => Ok(ReturnValue::None),
        "ALL_OLD" => Ok(ReturnValue::AllOld),
        "UPDATED_OLD" => Ok(ReturnValue::UpdatedOld),
        "ALL_NEW" => Ok(ReturnValue::AllNew),
        "UPDATED_NEW" => Ok(ReturnValue::UpdatedNew),
        _ => Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
            "Invalid return_values: '{}'. Must be one of: NONE, ALL_OLD, UPDATED_OLD, ALL_NEW, UPDATED_NEW",
            value
        ))),
    }
}

/// Prepare update_item by converting Python data to Rust.
#[allow(clippy::too_many_arguments)]
pub fn prepare_update_item(
    py: Python<'_>,
    table: &str,
    key: &Bound<'_, PyDict>,
    updates: Option<&Bound<'_, PyDict>>,
    update_expression: Option<String>,
    condition_expression: Option<String>,
    expression_attribute_names: Option<&Bound<'_, PyDict>>,
    expression_attribute_values: Option<&Bound<'_, PyDict>>,
    return_values_on_condition_check_failure: bool,
    return_values: Option<String>,
) -> PyResult<PreparedUpdateItem> {
    let dynamo_key = py_dict_to_attribute_values(py, key)?;

    let (final_update_expr, auto_names, auto_values) = if let Some(upd) = updates {
        build_set_expression(py, upd)?
    } else if let Some(expr) = update_expression {
        (expr, HashMap::new(), HashMap::new())
    } else {
        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            "Either 'updates' or 'update_expression' must be provided",
        ));
    };

    // Merge auto-generated names with user-provided names
    let mut names = auto_names;
    if let Some(user_names) = expression_attribute_names {
        for (k, v) in user_names.iter() {
            names.insert(k.extract::<String>()?, v.extract::<String>()?);
        }
    }

    // Merge auto-generated values with user-provided values
    let mut values = auto_values;
    if let Some(user_values) = expression_attribute_values {
        let dynamo_values = py_dict_to_attribute_values(py, user_values)?;
        for (placeholder, attr_value) in dynamo_values {
            values.insert(placeholder, attr_value);
        }
    }

    let return_on_failure = if return_values_on_condition_check_failure {
        Some(ReturnValuesOnConditionCheckFailure::AllOld)
    } else {
        None
    };

    let rv = match return_values {
        Some(ref s) if s != "NONE" => Some(parse_return_values(s)?),
        _ => None,
    };

    Ok(PreparedUpdateItem {
        table: table.to_string(),
        key: dynamo_key,
        update_expression: final_update_expr,
        condition_expression,
        expression_attribute_names: names,
        expression_attribute_values: values,
        return_values_on_condition_check_failure: return_on_failure,
        return_values: rv,
    })
}

/// Result of an update_item operation.
pub struct UpdateItemResult {
    pub metrics: OperationMetrics,
    pub attributes: Option<HashMap<String, AttributeValue>>,
}

/// Core async update_item operation.
pub async fn execute_update_item(
    client: Client,
    prepared: PreparedUpdateItem,
) -> Result<
    UpdateItemResult,
    (
        aws_sdk_dynamodb::error::SdkError<
            aws_sdk_dynamodb::operation::update_item::UpdateItemError,
        >,
        String,
        Option<HashMap<String, AttributeValue>>,
    ),
> {
    let has_return_values = prepared.return_values.is_some();

    let mut request = client
        .update_item()
        .table_name(&prepared.table)
        .set_key(Some(prepared.key))
        .update_expression(prepared.update_expression)
        .return_consumed_capacity(ReturnConsumedCapacity::Total);

    if let Some(condition) = prepared.condition_expression {
        request = request.condition_expression(condition);
    }

    for (placeholder, attr_name) in prepared.expression_attribute_names {
        request = request.expression_attribute_names(placeholder, attr_name);
    }

    for (placeholder, attr_value) in prepared.expression_attribute_values {
        request = request.expression_attribute_values(placeholder, attr_value);
    }

    if let Some(return_on_failure) = prepared.return_values_on_condition_check_failure {
        request = request.return_values_on_condition_check_failure(return_on_failure);
    }

    if let Some(rv) = prepared.return_values {
        request = request.return_values(rv);
    }

    let start = Instant::now();
    let result = request.send().await;
    let duration_ms = start.elapsed().as_secs_f64() * 1000.0;

    match result {
        Ok(output) => {
            let consumed_wcu = output.consumed_capacity().and_then(|c| c.capacity_units());

            let attributes = if has_return_values {
                output.attributes().cloned()
            } else {
                None
            };

            Ok(UpdateItemResult {
                metrics: OperationMetrics::with_capacity(duration_ms, None, consumed_wcu, None),
                attributes,
            })
        }
        Err(e) => {
            let item = extract_item_from_update_error(&e);
            Err((e, prepared.table, item))
        }
    }
}

/// Extract the item from a ConditionalCheckFailedException.
fn extract_item_from_update_error(
    err: &aws_sdk_dynamodb::error::SdkError<
        aws_sdk_dynamodb::operation::update_item::UpdateItemError,
    >,
) -> Option<HashMap<String, AttributeValue>> {
    use aws_sdk_dynamodb::operation::update_item::UpdateItemError;

    if let aws_sdk_dynamodb::error::SdkError::ServiceError(service_err) = err
        && let UpdateItemError::ConditionalCheckFailedException(ccf) = service_err.err()
    {
        return ccf.item().cloned();
    }
    None
}

/// Sync update_item - blocks until complete.
#[allow(clippy::too_many_arguments)]
pub fn sync_update_item(
    py: Python<'_>,
    client: &Client,
    runtime: &Arc<Runtime>,
    table: &str,
    key: &Bound<'_, PyDict>,
    updates: Option<&Bound<'_, PyDict>>,
    update_expression: Option<String>,
    condition_expression: Option<String>,
    expression_attribute_names: Option<&Bound<'_, PyDict>>,
    expression_attribute_values: Option<&Bound<'_, PyDict>>,
    return_values_on_condition_check_failure: bool,
    return_values: Option<String>,
) -> PyResult<(Option<Py<PyAny>>, OperationMetrics)> {
    let prepared = prepare_update_item(
        py,
        table,
        key,
        updates,
        update_expression,
        condition_expression,
        expression_attribute_names,
        expression_attribute_values,
        return_values_on_condition_check_failure,
        return_values,
    )?;

    let result = py.detach(|| runtime.block_on(execute_update_item(client.clone(), prepared)));

    match result {
        Ok(update_result) => {
            let py_attrs = match update_result.attributes {
                Some(attrs) => {
                    let dict = attribute_values_to_py_dict(py, attrs)?;
                    Some(dict.into())
                }
                None => None,
            };
            Ok((py_attrs, update_result.metrics))
        }
        Err((e, tbl, item)) => Err(map_sdk_error_with_item(py, e, Some(&tbl), item)),
    }
}

/// Async update_item - returns a Python awaitable (default).
#[allow(clippy::too_many_arguments)]
pub fn update_item<'py>(
    py: Python<'py>,
    client: Client,
    table: &str,
    key: &Bound<'_, PyDict>,
    updates: Option<&Bound<'_, PyDict>>,
    update_expression: Option<String>,
    condition_expression: Option<String>,
    expression_attribute_names: Option<&Bound<'_, PyDict>>,
    expression_attribute_values: Option<&Bound<'_, PyDict>>,
    return_values_on_condition_check_failure: bool,
    return_values: Option<String>,
) -> PyResult<Bound<'py, PyAny>> {
    let prepared = prepare_update_item(
        py,
        table,
        key,
        updates,
        update_expression,
        condition_expression,
        expression_attribute_names,
        expression_attribute_values,
        return_values_on_condition_check_failure,
        return_values,
    )?;

    pyo3_async_runtimes::tokio::future_into_py(py, async move {
        let result = execute_update_item(client, prepared).await;
        match result {
            Ok(update_result) => Python::attach(|py| {
                let py_attrs = match update_result.attributes {
                    Some(attrs) => {
                        let dict = attribute_values_to_py_dict(py, attrs)?;
                        Some(dict.unbind().into_any())
                    }
                    None => None,
                };
                Ok((py_attrs, update_result.metrics))
            }),
            Err((e, tbl, item)) => {
                Python::attach(|py| Err(map_sdk_error_with_item(py, e, Some(&tbl), item)))
            }
        }
    })
}

/// Build a SET update expression from a dict of field:value pairs.
#[allow(clippy::type_complexity)]
pub fn build_set_expression(
    py: Python<'_>,
    updates: &Bound<'_, PyDict>,
) -> PyResult<(
    String,
    HashMap<String, String>,
    HashMap<String, AttributeValue>,
)> {
    let mut set_parts = Vec::new();
    let mut names = HashMap::new();
    let mut values = HashMap::new();

    for (i, (k, v)) in updates.iter().enumerate() {
        let field: String = k.extract()?;
        let name_placeholder = format!("#f{}", i);
        let value_placeholder = format!(":v{}", i);

        set_parts.push(format!("{} = {}", name_placeholder, value_placeholder));
        names.insert(name_placeholder, field);

        let attr_value = py_to_attribute_value_direct(py, &v)?;
        values.insert(value_placeholder, attr_value);
    }

    let expression = format!("SET {}", set_parts.join(", "));
    Ok((expression, names, values))
}
