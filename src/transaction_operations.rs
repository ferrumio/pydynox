//! Transaction operations module for DynamoDB.
//!
//! Handles transactional read and write operations with all-or-nothing semantics.
//! All operations in a transaction either succeed together or fail together.

use aws_sdk_dynamodb::types::{
    ConditionCheck, Delete, Get, Put, TransactGetItem, TransactWriteItem, Update,
};
use aws_sdk_dynamodb::Client;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use std::sync::Arc;
use tokio::runtime::Runtime;

use crate::conversions::{attribute_values_to_py_dict, py_dict_to_attribute_values};
use crate::errors::map_sdk_error;

/// Maximum items per transaction (DynamoDB limit).
const TRANSACTION_MAX_ITEMS: usize = 100;

/// Execute a transactional write operation.
///
/// All operations run atomically. Either all succeed or all fail.
/// Use this when you need data consistency across multiple items.
///
/// # Arguments
///
/// * `py` - Python interpreter reference
/// * `client` - DynamoDB client
/// * `runtime` - Tokio runtime
/// * `operations` - List of operation dicts, each with:
///   - `type`: "put", "delete", "update", or "condition_check"
///   - `table`: Table name
///   - `item`: Item to put (for "put" type)
///   - `key`: Key dict (for "delete", "update", "condition_check")
///   - `update_expression`: Update expression (for "update" type)
///   - `condition_expression`: Optional condition expression
///   - `expression_attribute_names`: Optional name placeholders
///   - `expression_attribute_values`: Optional value placeholders
///
/// # Returns
///
/// Ok(()) on success, or an error if the transaction fails.
pub fn transact_write(
    py: Python<'_>,
    client: &Client,
    runtime: &Arc<Runtime>,
    operations: &Bound<'_, PyList>,
) -> PyResult<()> {
    if operations.is_empty() {
        return Ok(());
    }

    if operations.len() > TRANSACTION_MAX_ITEMS {
        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
            "Transaction exceeds maximum of {} items (got {})",
            TRANSACTION_MAX_ITEMS,
            operations.len()
        )));
    }

    let mut transact_items: Vec<TransactWriteItem> = Vec::new();

    for op in operations.iter() {
        let op_dict = op.cast::<PyDict>()?;
        let transact_item = build_transact_write_item(py, op_dict)?;
        transact_items.push(transact_item);
    }

    let client = client.clone();

    let result = runtime.block_on(async {
        client
            .transact_write_items()
            .set_transact_items(Some(transact_items))
            .send()
            .await
    });

    match result {
        Ok(_) => Ok(()),
        Err(e) => Err(map_sdk_error(e, None)),
    }
}

/// Build a TransactWriteItem from a Python dict.
fn build_transact_write_item(
    py: Python<'_>,
    op_dict: &Bound<'_, PyDict>,
) -> PyResult<TransactWriteItem> {
    let op_type: String = op_dict
        .get_item("type")?
        .ok_or_else(|| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>("Operation missing 'type' field")
        })?
        .extract()?;

    let table: String = op_dict
        .get_item("table")?
        .ok_or_else(|| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>("Operation missing 'table' field")
        })?
        .extract()?;

    match op_type.as_str() {
        "put" => build_put_item(py, op_dict, &table),
        "delete" => build_delete_item(py, op_dict, &table),
        "update" => build_update_item(py, op_dict, &table),
        "condition_check" => build_condition_check(py, op_dict, &table),
        _ => Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
            "Unknown operation type: '{}'. Use 'put', 'delete', 'update', or 'condition_check'",
            op_type
        ))),
    }
}

/// Build a Put transaction item.
fn build_put_item(
    py: Python<'_>,
    op_dict: &Bound<'_, PyDict>,
    table: &str,
) -> PyResult<TransactWriteItem> {
    let item_obj = op_dict.get_item("item")?.ok_or_else(|| {
        PyErr::new::<pyo3::exceptions::PyValueError, _>("Put operation missing 'item' field")
    })?;
    let item_dict = item_obj.cast::<PyDict>()?;
    let dynamo_item = py_dict_to_attribute_values(py, item_dict)?;

    let mut put_builder = Put::builder().table_name(table).set_item(Some(dynamo_item));

    if let Some(condition) = op_dict.get_item("condition_expression")? {
        let condition_str: String = condition.extract()?;
        put_builder = put_builder.condition_expression(condition_str);
    }

    if let Some(names_obj) = op_dict.get_item("expression_attribute_names")? {
        let names_dict = names_obj.cast::<PyDict>()?;
        for (k, v) in names_dict.iter() {
            let placeholder: String = k.extract()?;
            let attr_name: String = v.extract()?;
            put_builder = put_builder.expression_attribute_names(placeholder, attr_name);
        }
    }

    if let Some(values_obj) = op_dict.get_item("expression_attribute_values")? {
        let values_dict = values_obj.cast::<PyDict>()?;
        let dynamo_values = py_dict_to_attribute_values(py, values_dict)?;
        for (placeholder, attr_value) in dynamo_values {
            put_builder = put_builder.expression_attribute_values(placeholder, attr_value);
        }
    }

    let put = put_builder.build().map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Failed to build Put: {}", e))
    })?;

    Ok(TransactWriteItem::builder().put(put).build())
}

/// Build a Delete transaction item.
fn build_delete_item(
    py: Python<'_>,
    op_dict: &Bound<'_, PyDict>,
    table: &str,
) -> PyResult<TransactWriteItem> {
    let key_obj = op_dict.get_item("key")?.ok_or_else(|| {
        PyErr::new::<pyo3::exceptions::PyValueError, _>("Delete operation missing 'key' field")
    })?;
    let key_dict = key_obj.cast::<PyDict>()?;
    let dynamo_key = py_dict_to_attribute_values(py, key_dict)?;

    let mut delete_builder = Delete::builder()
        .table_name(table)
        .set_key(Some(dynamo_key));

    if let Some(condition) = op_dict.get_item("condition_expression")? {
        let condition_str: String = condition.extract()?;
        delete_builder = delete_builder.condition_expression(condition_str);
    }

    if let Some(names_obj) = op_dict.get_item("expression_attribute_names")? {
        let names_dict = names_obj.cast::<PyDict>()?;
        for (k, v) in names_dict.iter() {
            let placeholder: String = k.extract()?;
            let attr_name: String = v.extract()?;
            delete_builder = delete_builder.expression_attribute_names(placeholder, attr_name);
        }
    }

    if let Some(values_obj) = op_dict.get_item("expression_attribute_values")? {
        let values_dict = values_obj.cast::<PyDict>()?;
        let dynamo_values = py_dict_to_attribute_values(py, values_dict)?;
        for (placeholder, attr_value) in dynamo_values {
            delete_builder = delete_builder.expression_attribute_values(placeholder, attr_value);
        }
    }

    let delete = delete_builder.build().map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Failed to build Delete: {}", e))
    })?;

    Ok(TransactWriteItem::builder().delete(delete).build())
}

/// Build an Update transaction item.
fn build_update_item(
    py: Python<'_>,
    op_dict: &Bound<'_, PyDict>,
    table: &str,
) -> PyResult<TransactWriteItem> {
    let key_obj = op_dict.get_item("key")?.ok_or_else(|| {
        PyErr::new::<pyo3::exceptions::PyValueError, _>("Update operation missing 'key' field")
    })?;
    let key_dict = key_obj.cast::<PyDict>()?;
    let dynamo_key = py_dict_to_attribute_values(py, key_dict)?;

    let update_expr: String = op_dict
        .get_item("update_expression")?
        .ok_or_else(|| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Update operation missing 'update_expression' field",
            )
        })?
        .extract()?;

    let mut update_builder = Update::builder()
        .table_name(table)
        .set_key(Some(dynamo_key))
        .update_expression(update_expr);

    if let Some(condition) = op_dict.get_item("condition_expression")? {
        let condition_str: String = condition.extract()?;
        update_builder = update_builder.condition_expression(condition_str);
    }

    if let Some(names_obj) = op_dict.get_item("expression_attribute_names")? {
        let names_dict = names_obj.cast::<PyDict>()?;
        for (k, v) in names_dict.iter() {
            let placeholder: String = k.extract()?;
            let attr_name: String = v.extract()?;
            update_builder = update_builder.expression_attribute_names(placeholder, attr_name);
        }
    }

    if let Some(values_obj) = op_dict.get_item("expression_attribute_values")? {
        let values_dict = values_obj.cast::<PyDict>()?;
        let dynamo_values = py_dict_to_attribute_values(py, values_dict)?;
        for (placeholder, attr_value) in dynamo_values {
            update_builder = update_builder.expression_attribute_values(placeholder, attr_value);
        }
    }

    let update = update_builder.build().map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Failed to build Update: {}", e))
    })?;

    Ok(TransactWriteItem::builder().update(update).build())
}

/// Build a ConditionCheck transaction item.
fn build_condition_check(
    py: Python<'_>,
    op_dict: &Bound<'_, PyDict>,
    table: &str,
) -> PyResult<TransactWriteItem> {
    let key_obj = op_dict.get_item("key")?.ok_or_else(|| {
        PyErr::new::<pyo3::exceptions::PyValueError, _>(
            "ConditionCheck operation missing 'key' field",
        )
    })?;
    let key_dict = key_obj.cast::<PyDict>()?;
    let dynamo_key = py_dict_to_attribute_values(py, key_dict)?;

    let condition_expr: String = op_dict
        .get_item("condition_expression")?
        .ok_or_else(|| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "ConditionCheck operation missing 'condition_expression' field",
            )
        })?
        .extract()?;

    let mut check_builder = ConditionCheck::builder()
        .table_name(table)
        .set_key(Some(dynamo_key))
        .condition_expression(condition_expr);

    if let Some(names_obj) = op_dict.get_item("expression_attribute_names")? {
        let names_dict = names_obj.cast::<PyDict>()?;
        for (k, v) in names_dict.iter() {
            let placeholder: String = k.extract()?;
            let attr_name: String = v.extract()?;
            check_builder = check_builder.expression_attribute_names(placeholder, attr_name);
        }
    }

    if let Some(values_obj) = op_dict.get_item("expression_attribute_values")? {
        let values_dict = values_obj.cast::<PyDict>()?;
        let dynamo_values = py_dict_to_attribute_values(py, values_dict)?;
        for (placeholder, attr_value) in dynamo_values {
            check_builder = check_builder.expression_attribute_values(placeholder, attr_value);
        }
    }

    let check = check_builder.build().map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
            "Failed to build ConditionCheck: {}",
            e
        ))
    })?;

    Ok(TransactWriteItem::builder().condition_check(check).build())
}

// ========== TRANSACT GET ==========

/// Execute a transactional get operation.
///
/// Reads multiple items atomically. Either all reads succeed or all fail.
/// Use this when you need a consistent snapshot of multiple items.
///
/// # Arguments
///
/// * `py` - Python interpreter reference
/// * `client` - DynamoDB client
/// * `runtime` - Tokio runtime
/// * `gets` - List of get dicts, each with:
///   - `table`: Table name
///   - `key`: Key dict (pk and optional sk)
///   - `projection_expression`: Optional projection (saves RCU)
///   - `expression_attribute_names`: Optional name placeholders
///
/// # Returns
///
/// List of items (or None for items that don't exist).
pub fn transact_get(
    py: Python<'_>,
    client: &Client,
    runtime: &Arc<Runtime>,
    gets: &Bound<'_, PyList>,
) -> PyResult<Vec<Option<Py<PyAny>>>> {
    if gets.is_empty() {
        return Ok(vec![]);
    }

    if gets.len() > TRANSACTION_MAX_ITEMS {
        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
            "Transaction exceeds maximum of {} items (got {})",
            TRANSACTION_MAX_ITEMS,
            gets.len()
        )));
    }

    let mut transact_items: Vec<TransactGetItem> = Vec::new();

    for get in gets.iter() {
        let get_dict = get.cast::<PyDict>()?;
        let transact_item = build_transact_get_item(py, get_dict)?;
        transact_items.push(transact_item);
    }

    let client = client.clone();

    let result = runtime.block_on(async {
        client
            .transact_get_items()
            .set_transact_items(Some(transact_items))
            .send()
            .await
    });

    match result {
        Ok(output) => {
            let responses = output.responses.unwrap_or_default();
            let mut items: Vec<Option<Py<PyAny>>> = Vec::with_capacity(responses.len());

            for response in responses {
                if let Some(item) = response.item {
                    let py_dict = attribute_values_to_py_dict(py, item)?;
                    items.push(Some(py_dict.into_any().unbind()));
                } else {
                    items.push(None);
                }
            }

            Ok(items)
        }
        Err(e) => Err(map_sdk_error(e, None)),
    }
}

/// Build a TransactGetItem from a Python dict.
fn build_transact_get_item(
    py: Python<'_>,
    get_dict: &Bound<'_, PyDict>,
) -> PyResult<TransactGetItem> {
    let table: String = get_dict
        .get_item("table")?
        .ok_or_else(|| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>("Get operation missing 'table' field")
        })?
        .extract()?;

    let key_obj = get_dict.get_item("key")?.ok_or_else(|| {
        PyErr::new::<pyo3::exceptions::PyValueError, _>("Get operation missing 'key' field")
    })?;
    let key_dict = key_obj.cast::<PyDict>()?;
    let dynamo_key = py_dict_to_attribute_values(py, key_dict)?;

    let mut get_builder = Get::builder().table_name(table).set_key(Some(dynamo_key));

    if let Some(projection) = get_dict.get_item("projection_expression")? {
        let projection_str: String = projection.extract()?;
        get_builder = get_builder.projection_expression(projection_str);
    }

    if let Some(names_obj) = get_dict.get_item("expression_attribute_names")? {
        let names_dict = names_obj.cast::<PyDict>()?;
        for (k, v) in names_dict.iter() {
            let placeholder: String = k.extract()?;
            let attr_name: String = v.extract()?;
            get_builder = get_builder.expression_attribute_names(placeholder, attr_name);
        }
    }

    let get = get_builder.build().map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Failed to build Get: {}", e))
    })?;

    Ok(TransactGetItem::builder().get(get).build())
}

// ========== ASYNC VERSIONS ==========

/// Async version of transact_write.
///
/// Returns a Python awaitable that executes the transaction.
pub fn async_transact_write<'py>(
    py: Python<'py>,
    client: Client,
    operations: &Bound<'_, PyList>,
) -> PyResult<Bound<'py, PyAny>> {
    if operations.is_empty() {
        return pyo3_async_runtimes::tokio::future_into_py(py, async move {
            Ok(Python::attach(|py| py.None()))
        });
    }

    if operations.len() > TRANSACTION_MAX_ITEMS {
        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
            "Transaction exceeds maximum of {} items (got {})",
            TRANSACTION_MAX_ITEMS,
            operations.len()
        )));
    }

    let mut transact_items: Vec<TransactWriteItem> = Vec::new();

    for op in operations.iter() {
        let op_dict = op.cast::<PyDict>()?;
        let transact_item = build_transact_write_item(py, op_dict)?;
        transact_items.push(transact_item);
    }

    pyo3_async_runtimes::tokio::future_into_py(py, async move {
        let result = client
            .transact_write_items()
            .set_transact_items(Some(transact_items))
            .send()
            .await;

        match result {
            Ok(_) => Ok(Python::attach(|py| py.None())),
            Err(e) => Err(map_sdk_error(e, None)),
        }
    })
}

/// Async version of transact_get.
///
/// Returns a Python awaitable that reads multiple items atomically.
pub fn async_transact_get<'py>(
    py: Python<'py>,
    client: Client,
    gets: &Bound<'_, PyList>,
) -> PyResult<Bound<'py, PyAny>> {
    if gets.is_empty() {
        return pyo3_async_runtimes::tokio::future_into_py(py, async move {
            Ok(Python::attach(|py| {
                let list = pyo3::types::PyList::empty(py);
                list.into_any().unbind()
            }))
        });
    }

    if gets.len() > TRANSACTION_MAX_ITEMS {
        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
            "Transaction exceeds maximum of {} items (got {})",
            TRANSACTION_MAX_ITEMS,
            gets.len()
        )));
    }

    let mut transact_items: Vec<TransactGetItem> = Vec::new();

    for get in gets.iter() {
        let get_dict = get.cast::<PyDict>()?;
        let transact_item = build_transact_get_item(py, get_dict)?;
        transact_items.push(transact_item);
    }

    pyo3_async_runtimes::tokio::future_into_py(py, async move {
        let result = client
            .transact_get_items()
            .set_transact_items(Some(transact_items))
            .send()
            .await;

        match result {
            Ok(output) => Python::attach(|py| {
                let responses = output.responses.unwrap_or_default();
                let py_list = pyo3::types::PyList::empty(py);

                for response in responses {
                    if let Some(item) = response.item {
                        let py_dict = attribute_values_to_py_dict(py, item)?;
                        py_list.append(py_dict)?;
                    } else {
                        py_list.append(py.None())?;
                    }
                }

                Ok(py_list.into_any().unbind())
            }),
            Err(e) => Err(map_sdk_error(e, None)),
        }
    })
}
