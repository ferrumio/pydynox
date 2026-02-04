//! Transactional get operations for DynamoDB.

use aws_sdk_dynamodb::types::{AttributeValue, Get, ItemResponse, TransactGetItem};
use aws_sdk_dynamodb::Client;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use std::collections::HashMap;
use std::sync::Arc;
use tokio::runtime::Runtime;

use crate::conversions::{attribute_values_to_py_dict, py_dict_to_attribute_values};
use crate::errors::map_sdk_error;

/// Maximum items per transaction (DynamoDB limit).
const TRANSACTION_MAX_ITEMS: usize = 100;

// ========== PREPARE (needs GIL) ==========

/// Prepare transact_get - convert Python dicts to Rust types (needs GIL).
fn prepare_transact_get(
    py: Python<'_>,
    gets: &Bound<'_, PyList>,
) -> PyResult<Vec<TransactGetItem>> {
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

    let mut transact_items: Vec<TransactGetItem> = Vec::with_capacity(gets.len());

    for get in gets.iter() {
        let get_dict = get.cast::<PyDict>()?;
        let transact_item = build_transact_get_item(py, get_dict)?;
        transact_items.push(transact_item);
    }

    Ok(transact_items)
}

// ========== EXECUTE (async, no GIL) ==========

/// Raw result from transact_get (before Python conversion).
struct RawTransactGetResult {
    responses: Vec<Option<HashMap<String, AttributeValue>>>,
}

/// Execute transact_get asynchronously.
async fn execute_transact_get(
    client: Client,
    transact_items: Vec<TransactGetItem>,
) -> Result<
    RawTransactGetResult,
    aws_sdk_dynamodb::error::SdkError<
        aws_sdk_dynamodb::operation::transact_get_items::TransactGetItemsError,
    >,
> {
    if transact_items.is_empty() {
        return Ok(RawTransactGetResult { responses: vec![] });
    }

    let output = client
        .transact_get_items()
        .set_transact_items(Some(transact_items))
        .send()
        .await?;

    let responses: Vec<Option<HashMap<String, AttributeValue>>> = output
        .responses
        .unwrap_or_default()
        .into_iter()
        .map(|r: ItemResponse| r.item)
        .collect();

    Ok(RawTransactGetResult { responses })
}

// ========== PUBLIC API ==========

/// Sync version of transact_get. Blocks until complete.
///
/// Reads multiple items atomically. Either all reads succeed or all fail.
pub fn sync_transact_get(
    py: Python<'_>,
    client: &Client,
    runtime: &Arc<Runtime>,
    gets: &Bound<'_, PyList>,
) -> PyResult<Vec<Option<Py<PyAny>>>> {
    let transact_items = prepare_transact_get(py, gets)?;

    if transact_items.is_empty() {
        return Ok(vec![]);
    }

    let client = client.clone();
    let result = runtime.block_on(execute_transact_get(client, transact_items));

    match result {
        Ok(raw) => {
            let mut items: Vec<Option<Py<PyAny>>> = Vec::with_capacity(raw.responses.len());
            for response in raw.responses {
                if let Some(item) = response {
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

/// Execute a transactional get operation. Returns a Python awaitable.
///
/// Reads multiple items atomically. Either all reads succeed or all fail.
pub fn transact_get<'py>(
    py: Python<'py>,
    client: Client,
    gets: &Bound<'_, PyList>,
) -> PyResult<Bound<'py, PyAny>> {
    let transact_items = prepare_transact_get(py, gets)?;

    pyo3_async_runtimes::tokio::future_into_py(py, async move {
        let result = execute_transact_get(client, transact_items).await;

        match result {
            Ok(raw) => Python::attach(|py| {
                let py_list = PyList::empty(py);
                for response in raw.responses {
                    if let Some(item) = response {
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

// ========== BUILDERS ==========

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
