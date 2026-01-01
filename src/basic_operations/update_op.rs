//! Update item operation.

use aws_sdk_dynamodb::types::{AttributeValue, ReturnConsumedCapacity};
use aws_sdk_dynamodb::Client;
use pyo3::prelude::*;
use pyo3::types::PyDict;
use std::collections::HashMap;
use std::sync::Arc;
use std::time::Instant;
use tokio::runtime::Runtime;

use crate::conversions::{py_dict_to_attribute_value, py_dict_to_attribute_values};
use crate::errors::map_sdk_error;
use crate::metrics::OperationMetrics;
use crate::serialization::py_to_dynamo;

/// Prepared update_item data (converted from Python).
pub struct PreparedUpdateItem {
    pub table: String,
    pub key: HashMap<String, AttributeValue>,
    pub update_expression: String,
    pub condition_expression: Option<String>,
    pub expression_attribute_names: HashMap<String, String>,
    pub expression_attribute_values: HashMap<String, AttributeValue>,
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

    Ok(PreparedUpdateItem {
        table: table.to_string(),
        key: dynamo_key,
        update_expression: final_update_expr,
        condition_expression,
        expression_attribute_names: names,
        expression_attribute_values: values,
    })
}

/// Core async update_item operation.
pub async fn execute_update_item(
    client: Client,
    prepared: PreparedUpdateItem,
) -> Result<
    OperationMetrics,
    (
        aws_sdk_dynamodb::error::SdkError<
            aws_sdk_dynamodb::operation::update_item::UpdateItemError,
        >,
        String,
    ),
> {
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

/// Sync update_item - blocks until complete.
#[allow(clippy::too_many_arguments)]
pub fn update_item(
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
) -> PyResult<OperationMetrics> {
    let prepared = prepare_update_item(
        py,
        table,
        key,
        updates,
        update_expression,
        condition_expression,
        expression_attribute_names,
        expression_attribute_values,
    )?;

    let result = runtime.block_on(execute_update_item(client.clone(), prepared));

    match result {
        Ok(metrics) => Ok(metrics),
        Err((e, tbl)) => Err(map_sdk_error(e, Some(&tbl))),
    }
}

/// Async update_item - returns a Python awaitable.
#[allow(clippy::too_many_arguments)]
pub fn async_update_item<'py>(
    py: Python<'py>,
    client: Client,
    table: &str,
    key: &Bound<'_, PyDict>,
    updates: Option<&Bound<'_, PyDict>>,
    update_expression: Option<String>,
    condition_expression: Option<String>,
    expression_attribute_names: Option<&Bound<'_, PyDict>>,
    expression_attribute_values: Option<&Bound<'_, PyDict>>,
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
    )?;

    pyo3_async_runtimes::tokio::future_into_py(py, async move {
        let result = execute_update_item(client, prepared).await;
        match result {
            Ok(metrics) => Ok(metrics),
            Err((e, tbl)) => Err(map_sdk_error(e, Some(&tbl))),
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

        let dynamo_value = py_to_dynamo(py, &v)?;
        let attr_value = py_dict_to_attribute_value(py, dynamo_value.bind(py))?;
        values.insert(value_placeholder, attr_value);
    }

    let expression = format!("SET {}", set_parts.join(", "));
    Ok((expression, names, values))
}
