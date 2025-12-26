//! DynamoDB operations module.
//!
//! This module handles the conversion between Python dicts and DynamoDB
//! AttributeValue types, plus the actual DynamoDB operations.

use aws_sdk_dynamodb::types::AttributeValue;
use pyo3::prelude::*;
use pyo3::types::PyDict;
use std::collections::HashMap;

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
        let attr_value = py_dict_to_attribute_value(py, &dynamo_value.bind(py))?;
        result.insert(key, attr_value);
    }

    Ok(result)
}

/// Convert a single Python dict (in DynamoDB format) to an AttributeValue.
///
/// The dict should be in the format {"S": "value"}, {"N": "42"}, etc.
fn py_dict_to_attribute_value(
    py: Python<'_>,
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
        let py_list = list.downcast::<pyo3::types::PyList>()?;
        let mut items = Vec::new();
        for item in py_list.iter() {
            let item_dict = item.downcast::<PyDict>()?;
            items.push(py_dict_to_attribute_value(py, item_dict)?);
        }
        return Ok(AttributeValue::L(items));
    }

    // Map
    if let Some(map) = dict.get_item("M")? {
        let py_map = map.downcast::<PyDict>()?;
        let mut items = HashMap::new();
        for (k, v) in py_map.iter() {
            let key: String = k.extract()?;
            let value_dict = v.downcast::<PyDict>()?;
            items.insert(key, py_dict_to_attribute_value(py, value_dict)?);
        }
        return Ok(AttributeValue::M(items));
    }

    // String Set
    if let Some(ss) = dict.get_item("SS")? {
        let py_list = ss.downcast::<pyo3::types::PyList>()?;
        let strings: Vec<String> = py_list
            .iter()
            .map(|item| item.extract::<String>())
            .collect::<PyResult<Vec<_>>>()?;
        return Ok(AttributeValue::Ss(strings));
    }

    // Number Set
    if let Some(ns) = dict.get_item("NS")? {
        let py_list = ns.downcast::<pyo3::types::PyList>()?;
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
        let py_list = bs.downcast::<pyo3::types::PyList>()?;
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
fn attribute_value_to_py(py: Python<'_>, value: AttributeValue) -> PyResult<PyObject> {
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
            // Return the list directly, not wrapped in {"L": ...}
            return Ok(py_list.into_any().unbind());
        }
        AttributeValue::M(map) => {
            let py_map = PyDict::new(py);
            for (k, v) in map {
                let nested = attribute_value_to_py(py, v)?;
                py_map.set_item(k, nested)?;
            }
            // Return the dict directly, not wrapped in {"M": ...}
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
                // Convert string to number
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
