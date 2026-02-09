//! Type conversions between Python and DynamoDB AttributeValue.

use aws_sdk_dynamodb::primitives::Blob;
use aws_sdk_dynamodb::types::AttributeValue;
use pyo3::prelude::*;
use pyo3::types::{PyBool, PyBytes, PyDict, PyFloat, PyFrozenSet, PyInt, PyList, PySet, PyString};
use std::collections::HashMap;

/// Extract a HashMap<String, String> from an optional Python dict.
///
/// Used for expression_attribute_names conversion.
pub fn extract_string_map(
    dict: Option<&Bound<'_, PyDict>>,
) -> PyResult<Option<HashMap<String, String>>> {
    match dict {
        Some(d) => {
            let mut map = HashMap::new();
            for (k, v) in d.iter() {
                map.insert(k.extract::<String>()?, v.extract::<String>()?);
            }
            Ok(Some(map))
        }
        None => Ok(None),
    }
}

/// Convert a Python value directly to a DynamoDB AttributeValue.
///
/// This is the fast path — goes straight from PyAny to AttributeValue
/// without creating an intermediate Python dict.
///
/// Handles: str, bool, int, float, None, bytes, set, frozenset, list, dict.
#[allow(clippy::only_used_in_recursion)]
pub fn py_to_attribute_value_direct(
    py: Python<'_>,
    obj: &Bound<'_, PyAny>,
) -> PyResult<AttributeValue> {
    if obj.is_none() {
        Ok(AttributeValue::Null(true))
    } else if let Ok(s) = obj.cast::<PyString>() {
        Ok(AttributeValue::S(s.to_str()?.to_string()))
    } else if let Ok(b) = obj.cast::<PyBool>() {
        // Bool check must come before Int because bool is a subclass of int
        Ok(AttributeValue::Bool(b.is_true()))
    } else if obj.cast::<PyInt>().is_ok() || obj.cast::<PyFloat>().is_ok() {
        Ok(AttributeValue::N(obj.str()?.to_str()?.to_string()))
    } else if let Ok(bytes) = obj.cast::<PyBytes>() {
        Ok(AttributeValue::B(Blob::new(bytes.as_bytes().to_vec())))
    } else if let Ok(set) = obj.cast::<PySet>() {
        convert_set_direct(set.iter())
    } else if let Ok(frozen_set) = obj.cast::<PyFrozenSet>() {
        convert_set_direct(frozen_set.iter())
    } else if let Ok(list) = obj.cast::<PyList>() {
        let items: Vec<AttributeValue> = list
            .iter()
            .map(|item| py_to_attribute_value_direct(py, &item))
            .collect::<PyResult<Vec<_>>>()?;
        Ok(AttributeValue::L(items))
    } else if let Ok(dict) = obj.cast::<PyDict>() {
        let mut map = HashMap::new();
        for (k, v) in dict.iter() {
            let key: String = k.extract()?;
            let value = py_to_attribute_value_direct(py, &v)?;
            map.insert(key, value);
        }
        Ok(AttributeValue::M(map))
    } else {
        Err(PyErr::new::<pyo3::exceptions::PyTypeError, _>(format!(
            "Unsupported type for DynamoDB: {}. Supported types: str, int, float, bool, None, list, dict, bytes, set",
            obj.get_type().name()?
        )))
    }
}

/// Convert a Python set/frozenset directly to a DynamoDB set AttributeValue (SS, NS, or BS).
fn convert_set_direct<'py, I>(iter: I) -> PyResult<AttributeValue>
where
    I: Iterator<Item = Bound<'py, PyAny>>,
{
    let items: Vec<Bound<'py, PyAny>> = iter.collect();

    if items.is_empty() {
        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            "DynamoDB does not support empty sets",
        ));
    }

    let first = &items[0];

    if first.cast::<PyString>().is_ok() {
        let strings: Vec<String> = items
            .iter()
            .map(|item| {
                item.cast::<PyString>()
                    .map_err(|_| {
                        PyErr::new::<pyo3::exceptions::PyTypeError, _>(
                            "String set must contain only strings",
                        )
                    })?
                    .extract::<String>()
            })
            .collect::<PyResult<Vec<_>>>()?;
        Ok(AttributeValue::Ss(strings))
    } else if first.cast::<PyInt>().is_ok() || first.cast::<PyFloat>().is_ok() {
        let numbers: Vec<String> = items
            .iter()
            .map(|item| {
                if item.cast::<PyInt>().is_ok() || item.cast::<PyFloat>().is_ok() {
                    Ok(item.str()?.to_str()?.to_string())
                } else {
                    Err(PyErr::new::<pyo3::exceptions::PyTypeError, _>(
                        "Number set must contain only numbers",
                    ))
                }
            })
            .collect::<PyResult<Vec<_>>>()?;
        Ok(AttributeValue::Ns(numbers))
    } else if first.cast::<PyBytes>().is_ok() {
        let blobs: Vec<Blob> = items
            .iter()
            .map(|item| {
                let bytes = item.cast::<PyBytes>().map_err(|_| {
                    PyErr::new::<pyo3::exceptions::PyTypeError, _>(
                        "Binary set must contain only bytes",
                    )
                })?;
                Ok(Blob::new(bytes.as_bytes().to_vec()))
            })
            .collect::<PyResult<Vec<_>>>()?;
        Ok(AttributeValue::Bs(blobs))
    } else {
        Err(PyErr::new::<pyo3::exceptions::PyTypeError, _>(format!(
            "Unsupported set element type: {}. Sets can only contain strings, numbers, or bytes",
            first.get_type().name()?
        )))
    }
}

/// Convert a Python dict to a HashMap of DynamoDB AttributeValues.
///
/// Uses the direct path (no intermediate Python dict).
pub fn py_dict_to_attribute_values(
    py: Python<'_>,
    dict: &Bound<'_, PyDict>,
) -> PyResult<HashMap<String, AttributeValue>> {
    let mut result = HashMap::new();

    for (k, v) in dict.iter() {
        let key: String = k.extract()?;
        let attr_value = py_to_attribute_value_direct(py, &v)?;
        result.insert(key, attr_value);
    }

    Ok(result)
}

/// Convert a HashMap of DynamoDB AttributeValues to a Python dict.
///
/// Uses direct conversion for better performance.
pub fn attribute_values_to_py_dict(
    py: Python<'_>,
    item: HashMap<String, AttributeValue>,
) -> PyResult<Bound<'_, PyDict>> {
    let result = PyDict::new(py);

    for (key, value) in item {
        let py_value = attribute_value_to_py_direct(py, value)?;
        result.set_item(key, py_value)?;
    }

    Ok(result)
}

/// Convert a DynamoDB AttributeValue directly to a native Python object.
///
/// This is the fast path - converts directly without intermediate dict.
/// Used for query/scan results where we want native Python values.
fn attribute_value_to_py_direct(py: Python<'_>, value: AttributeValue) -> PyResult<Py<PyAny>> {
    match value {
        AttributeValue::S(s) => Ok(s.into_pyobject(py)?.unbind().into_any()),
        AttributeValue::N(n) => {
            // Parse number - int or float
            if n.contains('.') || n.contains('e') || n.contains('E') {
                let f: f64 = n.parse().map_err(|_| {
                    PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                        "Invalid number: {}",
                        n
                    ))
                })?;
                Ok(f.into_pyobject(py)?.unbind().into_any())
            } else {
                let i: i64 = n.parse().map_err(|_| {
                    PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                        "Invalid number: {}",
                        n
                    ))
                })?;
                Ok(i.into_pyobject(py)?.unbind().into_any())
            }
        }
        AttributeValue::Bool(b) => Ok(b.into_pyobject(py)?.to_owned().unbind().into_any()),
        AttributeValue::Null(_) => Ok(py.None()),
        AttributeValue::B(b) => {
            // Return bytes directly
            let bytes = pyo3::types::PyBytes::new(py, b.as_ref());
            Ok(bytes.into_any().unbind())
        }
        AttributeValue::L(list) => {
            let py_list = pyo3::types::PyList::empty(py);
            for item in list {
                let nested = attribute_value_to_py_direct(py, item)?;
                py_list.append(nested)?;
            }
            Ok(py_list.into_any().unbind())
        }
        AttributeValue::M(map) => {
            let py_map = PyDict::new(py);
            for (k, v) in map {
                let nested = attribute_value_to_py_direct(py, v)?;
                py_map.set_item(k, nested)?;
            }
            Ok(py_map.into_any().unbind())
        }
        AttributeValue::Ss(ss) => {
            let py_set = pyo3::types::PySet::empty(py)?;
            for s in ss {
                py_set.add(s)?;
            }
            Ok(py_set.into_any().unbind())
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
            Ok(py_set.into_any().unbind())
        }
        AttributeValue::Bs(bs) => {
            let py_set = pyo3::types::PySet::empty(py)?;
            for b in bs {
                let bytes = pyo3::types::PyBytes::new(py, b.as_ref());
                py_set.add(bytes)?;
            }
            Ok(py_set.into_any().unbind())
        }
        _ => Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            "Unknown DynamoDB AttributeValue type",
        )),
    }
}
