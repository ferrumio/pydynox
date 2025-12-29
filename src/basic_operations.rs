//! Basic operations module for type conversions.
//!
//! This module handles the conversion between Python dicts and DynamoDB
//! AttributeValue types.

use aws_sdk_dynamodb::types::AttributeValue;
use aws_sdk_dynamodb::Client;
use pyo3::prelude::*;
use pyo3::types::PyDict;
use std::collections::HashMap;
use std::sync::Arc;
use tokio::runtime::Runtime;

use crate::errors::map_sdk_error;
use crate::serialization::{dynamo_to_py, py_to_dynamo};

/// Convert a Python dict to a HashMap of DynamoDB AttributeValues.
///
/// Iterates over the Python dict and converts each value to DynamoDB format.
///
/// # Arguments
///
/// * `py` - Python interpreter reference
/// * `dict` - The Python dict to convert
///
/// # Returns
///
/// A HashMap ready for DynamoDB SDK calls.
pub fn py_dict_to_attribute_values(
    py: Python<'_>,
    dict: &Bound<'_, PyDict>,
) -> PyResult<HashMap<String, AttributeValue>> {
    let mut result = HashMap::new();

    for (k, v) in dict.iter() {
        let key: String = k.extract()?;
        let dynamo_value = py_to_dynamo(py, &v)?;
        let attr_value = py_dict_to_attribute_value(py, dynamo_value.bind(py))?;
        result.insert(key, attr_value);
    }

    Ok(result)
}

/// Convert a single Python dict (in DynamoDB format) to an AttributeValue.
///
/// The dict should be in the format {"S": "value"}, {"N": "42"}, etc.
pub fn py_dict_to_attribute_value(
    _py: Python<'_>,
    dict: &Bound<'_, PyDict>,
) -> PyResult<AttributeValue> {
    // String
    if let Some(s) = dict.get_item("S")? {
        let s_str: String = s.extract()?;
        return Ok(AttributeValue::S(s_str));
    }

    // Number
    if let Some(n) = dict.get_item("N")? {
        let n_str: String = n.extract()?;
        return Ok(AttributeValue::N(n_str));
    }

    // Boolean
    if let Some(b) = dict.get_item("BOOL")? {
        let b_val: bool = b.extract()?;
        return Ok(AttributeValue::Bool(b_val));
    }

    // Null
    if dict.get_item("NULL")?.is_some() {
        return Ok(AttributeValue::Null(true));
    }

    // Binary
    if let Some(b) = dict.get_item("B")? {
        let b_str: String = b.extract()?;
        use aws_sdk_dynamodb::primitives::Blob;
        use base64::Engine;
        let bytes = base64::engine::general_purpose::STANDARD
            .decode(&b_str)
            .map_err(|e| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                    "Invalid base64 encoding: {}",
                    e
                ))
            })?;
        return Ok(AttributeValue::B(Blob::new(bytes)));
    }

    // List
    if let Some(list) = dict.get_item("L")? {
        let py_list = list.cast::<pyo3::types::PyList>()?;
        let mut items = Vec::new();
        for item in py_list.iter() {
            let item_dict = item.cast::<PyDict>()?;
            items.push(py_dict_to_attribute_value(_py, item_dict)?);
        }
        return Ok(AttributeValue::L(items));
    }

    // Map
    if let Some(map) = dict.get_item("M")? {
        let py_map = map.cast::<PyDict>()?;
        let mut items = HashMap::new();
        for (k, v) in py_map.iter() {
            let key: String = k.extract()?;
            let value_dict = v.cast::<PyDict>()?;
            items.insert(key, py_dict_to_attribute_value(_py, value_dict)?);
        }
        return Ok(AttributeValue::M(items));
    }

    // String Set
    if let Some(ss) = dict.get_item("SS")? {
        let py_list = ss.cast::<pyo3::types::PyList>()?;
        let strings: Vec<String> = py_list
            .iter()
            .map(|item| item.extract::<String>())
            .collect::<PyResult<Vec<_>>>()?;
        return Ok(AttributeValue::Ss(strings));
    }

    // Number Set
    if let Some(ns) = dict.get_item("NS")? {
        let py_list = ns.cast::<pyo3::types::PyList>()?;
        let numbers: Vec<String> = py_list
            .iter()
            .map(|item| item.extract::<String>())
            .collect::<PyResult<Vec<_>>>()?;
        return Ok(AttributeValue::Ns(numbers));
    }

    // Binary Set
    if let Some(bs) = dict.get_item("BS")? {
        use aws_sdk_dynamodb::primitives::Blob;
        use base64::Engine;
        let py_list = bs.cast::<pyo3::types::PyList>()?;
        let mut blobs = Vec::new();
        for item in py_list.iter() {
            let b_str: String = item.extract()?;
            let bytes = base64::engine::general_purpose::STANDARD
                .decode(&b_str)
                .map_err(|e| {
                    PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                        "Invalid base64 encoding: {}",
                        e
                    ))
                })?;
            blobs.push(Blob::new(bytes));
        }
        return Ok(AttributeValue::Bs(blobs));
    }

    Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
        "Unknown DynamoDB AttributeValue type",
    ))
}

/// Convert a HashMap of DynamoDB AttributeValues to a Python dict.
///
/// # Arguments
///
/// * `py` - Python interpreter reference
/// * `item` - The DynamoDB item to convert
///
/// # Returns
///
/// A Python dict with native Python values.
pub fn attribute_values_to_py_dict(
    py: Python<'_>,
    item: HashMap<String, AttributeValue>,
) -> PyResult<Bound<'_, PyDict>> {
    let result = PyDict::new(py);

    for (key, value) in item {
        let py_value = attribute_value_to_py(py, value)?;
        result.set_item(key, py_value)?;
    }

    Ok(result)
}

/// Convert a single DynamoDB AttributeValue to a Python object.
fn attribute_value_to_py(py: Python<'_>, value: AttributeValue) -> PyResult<Py<PyAny>> {
    let dict = PyDict::new(py);

    match value {
        AttributeValue::S(s) => {
            dict.set_item("S", s)?;
        }
        AttributeValue::N(n) => {
            dict.set_item("N", n)?;
        }
        AttributeValue::Bool(b) => {
            dict.set_item("BOOL", b)?;
        }
        AttributeValue::Null(_) => {
            dict.set_item("NULL", true)?;
        }
        AttributeValue::B(b) => {
            use base64::Engine;
            let encoded = base64::engine::general_purpose::STANDARD.encode(b.as_ref());
            dict.set_item("B", encoded)?;
        }
        AttributeValue::L(list) => {
            let py_list = pyo3::types::PyList::empty(py);
            for item in list {
                let nested = attribute_value_to_py(py, item)?;
                py_list.append(nested)?;
            }
            return Ok(py_list.into_any().unbind());
        }
        AttributeValue::M(map) => {
            let py_map = PyDict::new(py);
            for (k, v) in map {
                let nested = attribute_value_to_py(py, v)?;
                py_map.set_item(k, nested)?;
            }
            return Ok(py_map.into_any().unbind());
        }
        AttributeValue::Ss(ss) => {
            let py_set = pyo3::types::PySet::empty(py)?;
            for s in ss {
                py_set.add(s)?;
            }
            return Ok(py_set.into_any().unbind());
        }
        AttributeValue::Ns(ns) => {
            let py_set = pyo3::types::PySet::empty(py)?;
            for n in ns {
                if n.contains('.') || n.contains('e') || n.contains('E') {
                    let f: f64 = n.parse().map_err(|_| {
                        PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                            "Invalid number: {}",
                            n
                        ))
                    })?;
                    py_set.add(f)?;
                } else {
                    let i: i64 = n.parse().map_err(|_| {
                        PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                            "Invalid number: {}",
                            n
                        ))
                    })?;
                    py_set.add(i)?;
                }
            }
            return Ok(py_set.into_any().unbind());
        }
        AttributeValue::Bs(bs) => {
            let py_set = pyo3::types::PySet::empty(py)?;
            for b in bs {
                let bytes = pyo3::types::PyBytes::new(py, b.as_ref());
                py_set.add(bytes)?;
            }
            return Ok(py_set.into_any().unbind());
        }
        _ => {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Unknown DynamoDB AttributeValue type",
            ));
        }
    }

    dynamo_to_py(py, &dict)
}

// ============================================================================
// DynamoDB Basic Operations
// ============================================================================

/// Put an item into a DynamoDB table.
pub fn put_item(
    py: Python<'_>,
    client: &Client,
    runtime: &Arc<Runtime>,
    table: &str,
    item: &Bound<'_, PyDict>,
) -> PyResult<()> {
    let dynamo_item = py_dict_to_attribute_values(py, item)?;

    let client = client.clone();
    let table_name = table.to_string();

    let result = runtime.block_on(async {
        client
            .put_item()
            .table_name(table_name)
            .set_item(Some(dynamo_item))
            .send()
            .await
    });

    match result {
        Ok(_) => Ok(()),
        Err(e) => Err(map_sdk_error(e, Some(table))),
    }
}

/// Get an item from a DynamoDB table by its key.
pub fn get_item(
    py: Python<'_>,
    client: &Client,
    runtime: &Arc<Runtime>,
    table: &str,
    key: &Bound<'_, PyDict>,
) -> PyResult<Option<Py<PyAny>>> {
    let dynamo_key = py_dict_to_attribute_values(py, key)?;

    let client = client.clone();
    let table_name = table.to_string();

    let result = runtime.block_on(async {
        client
            .get_item()
            .table_name(table_name)
            .set_key(Some(dynamo_key))
            .send()
            .await
    });

    match result {
        Ok(output) => {
            if let Some(item) = output.item {
                let py_dict = attribute_values_to_py_dict(py, item)?;
                Ok(Some(py_dict.into_any().unbind()))
            } else {
                Ok(None)
            }
        }
        Err(e) => Err(map_sdk_error(e, Some(table))),
    }
}

/// Delete an item from a DynamoDB table.
#[allow(clippy::too_many_arguments)]
pub fn delete_item(
    py: Python<'_>,
    client: &Client,
    runtime: &Arc<Runtime>,
    table: &str,
    key: &Bound<'_, PyDict>,
    condition_expression: Option<String>,
    expression_attribute_names: Option<&Bound<'_, PyDict>>,
    expression_attribute_values: Option<&Bound<'_, PyDict>>,
) -> PyResult<()> {
    let dynamo_key = py_dict_to_attribute_values(py, key)?;

    let client = client.clone();
    let table_name = table.to_string();

    let mut request = client
        .delete_item()
        .table_name(table_name)
        .set_key(Some(dynamo_key));

    if let Some(condition) = condition_expression {
        request = request.condition_expression(condition);
    }

    if let Some(names) = expression_attribute_names {
        for (k, v) in names.iter() {
            let placeholder: String = k.extract()?;
            let attr_name: String = v.extract()?;
            request = request.expression_attribute_names(placeholder, attr_name);
        }
    }

    if let Some(values) = expression_attribute_values {
        let dynamo_values = py_dict_to_attribute_values(py, values)?;
        for (placeholder, attr_value) in dynamo_values {
            request = request.expression_attribute_values(placeholder, attr_value);
        }
    }

    let result = runtime.block_on(async { request.send().await });

    match result {
        Ok(_) => Ok(()),
        Err(e) => Err(map_sdk_error(e, Some(table))),
    }
}

/// Update an item in a DynamoDB table.
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
) -> PyResult<()> {
    let dynamo_key = py_dict_to_attribute_values(py, key)?;

    let client = client.clone();
    let table_name = table.to_string();

    let mut request = client
        .update_item()
        .table_name(table_name)
        .set_key(Some(dynamo_key));

    let (final_update_expr, auto_names, auto_values) = if let Some(upd) = updates {
        build_set_expression(py, upd)?
    } else if let Some(expr) = update_expression {
        (expr, HashMap::new(), HashMap::new())
    } else {
        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            "Either 'updates' or 'update_expression' must be provided",
        ));
    };

    request = request.update_expression(final_update_expr);

    for (placeholder, attr_name) in auto_names {
        request = request.expression_attribute_names(placeholder, attr_name);
    }
    if let Some(names) = expression_attribute_names {
        for (k, v) in names.iter() {
            let placeholder: String = k.extract()?;
            let attr_name: String = v.extract()?;
            request = request.expression_attribute_names(placeholder, attr_name);
        }
    }

    for (placeholder, attr_value) in auto_values {
        request = request.expression_attribute_values(placeholder, attr_value);
    }
    if let Some(values) = expression_attribute_values {
        let dynamo_values = py_dict_to_attribute_values(py, values)?;
        for (placeholder, attr_value) in dynamo_values {
            request = request.expression_attribute_values(placeholder, attr_value);
        }
    }

    if let Some(condition) = condition_expression {
        request = request.condition_expression(condition);
    }

    let result = runtime.block_on(async { request.send().await });

    match result {
        Ok(_) => Ok(()),
        Err(e) => Err(map_sdk_error(e, Some(table))),
    }
}

/// Build a SET update expression from a dict of field:value pairs.
#[allow(clippy::type_complexity)]
fn build_set_expression(
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

// ============================================================================
// Query Operation
// ============================================================================

/// Query result containing items and pagination info.
pub struct QueryResult {
    pub items: Vec<Py<PyAny>>,
    pub last_evaluated_key: Option<Py<PyAny>>,
}

/// Query items from a DynamoDB table.
///
/// # Arguments
///
/// * `py` - Python interpreter reference
/// * `client` - DynamoDB client
/// * `runtime` - Tokio runtime
/// * `table` - Table name
/// * `key_condition_expression` - Key condition expression (required)
/// * `filter_expression` - Optional filter expression
/// * `expression_attribute_names` - Optional name placeholders
/// * `expression_attribute_values` - Optional value placeholders
/// * `limit` - Optional max items to return
/// * `exclusive_start_key` - Optional key to start from (for pagination)
/// * `scan_index_forward` - Sort order (true = ascending, false = descending)
/// * `index_name` - Optional GSI or LSI name
#[allow(clippy::too_many_arguments)]
pub fn query(
    py: Python<'_>,
    client: &Client,
    runtime: &Arc<Runtime>,
    table: &str,
    key_condition_expression: &str,
    filter_expression: Option<String>,
    expression_attribute_names: Option<&Bound<'_, PyDict>>,
    expression_attribute_values: Option<&Bound<'_, PyDict>>,
    limit: Option<i32>,
    exclusive_start_key: Option<&Bound<'_, PyDict>>,
    scan_index_forward: Option<bool>,
    index_name: Option<String>,
) -> PyResult<QueryResult> {
    let client = client.clone();
    let table_name = table.to_string();
    let key_cond = key_condition_expression.to_string();

    let mut request = client
        .query()
        .table_name(table_name.clone())
        .key_condition_expression(key_cond);

    if let Some(filter) = filter_expression {
        request = request.filter_expression(filter);
    }

    if let Some(names) = expression_attribute_names {
        for (k, v) in names.iter() {
            let placeholder: String = k.extract()?;
            let attr_name: String = v.extract()?;
            request = request.expression_attribute_names(placeholder, attr_name);
        }
    }

    if let Some(values) = expression_attribute_values {
        let dynamo_values = py_dict_to_attribute_values(py, values)?;
        for (placeholder, attr_value) in dynamo_values {
            request = request.expression_attribute_values(placeholder, attr_value);
        }
    }

    if let Some(n) = limit {
        request = request.limit(n);
    }

    if let Some(start_key) = exclusive_start_key {
        let dynamo_key = py_dict_to_attribute_values(py, start_key)?;
        request = request.set_exclusive_start_key(Some(dynamo_key));
    }

    if let Some(forward) = scan_index_forward {
        request = request.scan_index_forward(forward);
    }

    if let Some(idx) = index_name {
        request = request.index_name(idx);
    }

    let result = runtime.block_on(async { request.send().await });

    match result {
        Ok(output) => {
            let mut items = Vec::new();
            if let Some(dynamo_items) = output.items {
                for item in dynamo_items {
                    let py_dict = attribute_values_to_py_dict(py, item)?;
                    items.push(py_dict.into_any().unbind());
                }
            }

            let last_key = if let Some(lek) = output.last_evaluated_key {
                let py_dict = attribute_values_to_py_dict(py, lek)?;
                Some(py_dict.into_any().unbind())
            } else {
                None
            };

            Ok(QueryResult {
                items,
                last_evaluated_key: last_key,
            })
        }
        Err(e) => Err(map_sdk_error(e, Some(table))),
    }
}
