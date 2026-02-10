//! Transactional write operations for DynamoDB.

use aws_sdk_dynamodb::Client;
use aws_sdk_dynamodb::types::{ConditionCheck, Delete, Put, TransactWriteItem, Update};
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use std::sync::Arc;
use tokio::runtime::Runtime;

use crate::conversions::py_dict_to_attribute_values;
use crate::errors::map_sdk_error;

/// Maximum items per transaction (DynamoDB limit).
const TRANSACTION_MAX_ITEMS: usize = 100;

// ========== PREPARE (needs GIL) ==========

/// Prepare transact_write - convert Python dicts to Rust types (needs GIL).
fn prepare_transact_write(
    py: Python<'_>,
    operations: &Bound<'_, PyList>,
) -> PyResult<Vec<TransactWriteItem>> {
    if operations.is_empty() {
        return Ok(vec![]);
    }

    if operations.len() > TRANSACTION_MAX_ITEMS {
        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
            "Transaction exceeds maximum of {} items (got {})",
            TRANSACTION_MAX_ITEMS,
            operations.len()
        )));
    }

    let mut transact_items: Vec<TransactWriteItem> = Vec::with_capacity(operations.len());

    for op in operations.iter() {
        let op_dict = op.cast::<PyDict>()?;
        let transact_item = build_transact_write_item(py, op_dict)?;
        transact_items.push(transact_item);
    }

    Ok(transact_items)
}

// ========== EXECUTE (async, no GIL) ==========

/// Execute transact_write asynchronously.
async fn execute_transact_write(
    client: Client,
    transact_items: Vec<TransactWriteItem>,
) -> Result<
    (),
    aws_sdk_dynamodb::error::SdkError<
        aws_sdk_dynamodb::operation::transact_write_items::TransactWriteItemsError,
    >,
> {
    if transact_items.is_empty() {
        return Ok(());
    }

    client
        .transact_write_items()
        .set_transact_items(Some(transact_items))
        .send()
        .await?;

    Ok(())
}

// ========== PUBLIC API ==========

/// Sync version of transact_write. Blocks until complete.
///
/// All operations run atomically. Either all succeed or all fail.
pub fn sync_transact_write(
    py: Python<'_>,
    client: &Client,
    runtime: &Arc<Runtime>,
    operations: &Bound<'_, PyList>,
) -> PyResult<()> {
    let transact_items = prepare_transact_write(py, operations)?;

    if transact_items.is_empty() {
        return Ok(());
    }

    let client = client.clone();
    let result = py.detach(|| runtime.block_on(execute_transact_write(client, transact_items)));

    match result {
        Ok(()) => Ok(()),
        Err(e) => Err(map_sdk_error(e, None)),
    }
}

/// Execute a transactional write operation. Returns a Python awaitable.
///
/// All operations run atomically. Either all succeed or all fail.
pub fn transact_write<'py>(
    py: Python<'py>,
    client: Client,
    operations: &Bound<'_, PyList>,
) -> PyResult<Bound<'py, PyAny>> {
    let transact_items = prepare_transact_write(py, operations)?;

    pyo3_async_runtimes::tokio::future_into_py(py, async move {
        let result = execute_transact_write(client, transact_items).await;

        match result {
            Ok(()) => Ok(Python::attach(|py| py.None())),
            Err(e) => Err(map_sdk_error(e, None)),
        }
    })
}

// ========== BUILDERS ==========

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
