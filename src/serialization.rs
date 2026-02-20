//! Serialization module for converting between Python and DynamoDB types.
//!
//! DynamoDB uses a specific format for attribute values where each value
//! is wrapped in a type descriptor (S for string, N for number, etc.).
//!
//! This module handles the conversion:
//! - Python → DynamoDB: `py_to_dynamo`
//! - DynamoDB → Python: `dynamo_to_py`
//!
//! ## Supported Types
//!
//! | Python Type | DynamoDB Type | Format |
//! |-------------|---------------|--------|
//! | str | S | `{"S": "hello"}` |
//! | int, float | N | `{"N": "42"}` |
//! | bool | BOOL | `{"BOOL": true}` |
//! | None | NULL | `{"NULL": true}` |
//! | list | L | `{"L": [...]}` |
//! | dict | M | `{"M": {...}}` |
//! | bytes | B | `{"B": "base64..."}` |
//! | set[str] | SS | `{"SS": ["a", "b"]}` |
//! | set[int/float] | NS | `{"NS": ["1", "2"]}` |
//! | set[bytes] | BS | `{"BS": ["base64..."]}` |

use crate::conversions::parse_number_to_py;
use base64::Engine;
use pyo3::prelude::*;
use pyo3::types::{PyBool, PyBytes, PyDict, PyFloat, PyFrozenSet, PyInt, PyList, PySet, PyString};
use std::collections::HashMap;

/// Convert a Python object to a DynamoDB AttributeValue representation.
///
/// DynamoDB AttributeValue format uses type descriptors:
/// - `{"S": "hello"}` for strings
/// - `{"N": "42"}` for numbers (stored as strings)
/// - `{"BOOL": true}` for booleans
/// - `{"L": [...]}` for lists
/// - `{"M": {...}}` for maps/dicts
/// - `{"NULL": true}` for None
/// - `{"B": "base64..."}` for binary data
/// - `{"SS": ["a", "b"]}` for string sets
/// - `{"NS": ["1", "2"]}` for number sets
/// - `{"BS": ["base64..."]}` for binary sets
///
/// # Arguments
///
/// * `py` - Python interpreter reference
/// * `obj` - The Python object to convert
///
/// # Returns
///
/// A Python dict in DynamoDB AttributeValue format.
///
/// # Errors
///
/// Returns TypeError if the Python type is not supported.
///
/// # Examples
///
/// ```python
/// from pydynox._rust import py_to_dynamo
///
/// # String
/// result = py_to_dynamo("hello")
/// assert result == {"S": "hello"}
///
/// # Number
/// result = py_to_dynamo(42)
/// assert result == {"N": "42"}
///
/// # Boolean
/// result = py_to_dynamo(True)
/// assert result == {"BOOL": True}
///
/// # List
/// result = py_to_dynamo([1, "two"])
/// assert result == {"L": [{"N": "1"}, {"S": "two"}]}
///
/// # Map (dict)
/// result = py_to_dynamo({"name": "John", "age": 30})
/// assert result == {"M": {"name": {"S": "John"}, "age": {"N": "30"}}}
/// ```
pub fn py_to_dynamo<'py>(py: Python<'py>, obj: &Bound<'py, PyAny>) -> PyResult<Py<PyDict>> {
    let result = PyDict::new(py);

    if obj.is_none() {
        result.set_item("NULL", true)?;
    } else if let Ok(s) = obj.cast::<PyString>() {
        result.set_item("S", s.to_str()?)?;
    } else if let Ok(b) = obj.cast::<PyBool>() {
        // Note: PyBool check must come before PyInt because bool is a subclass of int
        result.set_item("BOOL", b.is_true())?;
    } else if obj.cast::<PyInt>().is_ok() || obj.cast::<PyFloat>().is_ok() {
        // DynamoDB stores numbers as strings
        result.set_item("N", obj.str()?.to_str()?)?;
    } else if let Ok(bytes) = obj.cast::<PyBytes>() {
        // Binary data - encode as base64
        let encoded = base64::engine::general_purpose::STANDARD.encode(bytes.as_bytes());
        result.set_item("B", encoded)?;
    } else if let Ok(set) = obj.cast::<PySet>() {
        convert_set_to_dynamo(py, set.iter(), &result)?;
    } else if let Ok(frozen_set) = obj.cast::<PyFrozenSet>() {
        convert_set_to_dynamo(py, frozen_set.iter(), &result)?;
    } else if let Ok(list) = obj.cast::<PyList>() {
        let items: Vec<Py<PyDict>> = list
            .iter()
            .map(|item| py_to_dynamo(py, &item))
            .collect::<PyResult<Vec<_>>>()?;
        result.set_item("L", items)?;
    } else if let Ok(dict) = obj.cast::<PyDict>() {
        let map: HashMap<String, Py<PyDict>> = dict
            .iter()
            .map(|(k, v)| {
                let key = k.extract::<String>()?;
                let value = py_to_dynamo(py, &v)?;
                Ok((key, value))
            })
            .collect::<PyResult<HashMap<_, _>>>()?;
        result.set_item("M", map)?;
    } else {
        return Err(PyErr::new::<pyo3::exceptions::PyTypeError, _>(format!(
            "Unsupported type for DynamoDB: {}. Supported types: str, int, float, bool, None, list, dict, bytes, set",
            obj.get_type().name()?
        )));
    }

    Ok(result.unbind())
}

/// Convert a Python set to DynamoDB set format (SS, NS, or BS).
///
/// DynamoDB sets must be homogeneous (all same type).
/// Empty sets are not allowed in DynamoDB.
fn convert_set_to_dynamo<'py, I>(
    _py: Python<'py>,
    iter: I,
    result: &Bound<'py, PyDict>,
) -> PyResult<()>
where
    I: Iterator<Item = Bound<'py, PyAny>>,
{
    let items: Vec<Bound<'py, PyAny>> = iter.collect();

    if items.is_empty() {
        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            "DynamoDB does not support empty sets",
        ));
    }

    // Check the type of the first element to determine set type
    let first = &items[0];

    if first.cast::<PyString>().is_ok() {
        // String Set (SS)
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
        result.set_item("SS", strings)?;
    } else if first.cast::<PyInt>().is_ok() || first.cast::<PyFloat>().is_ok() {
        // Number Set (NS) - stored as strings
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
        result.set_item("NS", numbers)?;
    } else if first.cast::<PyBytes>().is_ok() {
        // Binary Set (BS) - encode each as base64
        let binaries: Vec<String> = items
            .iter()
            .map(|item| {
                let bytes = item.cast::<PyBytes>().map_err(|_| {
                    PyErr::new::<pyo3::exceptions::PyTypeError, _>(
                        "Binary set must contain only bytes",
                    )
                })?;
                Ok(base64::engine::general_purpose::STANDARD.encode(bytes.as_bytes()))
            })
            .collect::<PyResult<Vec<_>>>()?;
        result.set_item("BS", binaries)?;
    } else {
        return Err(PyErr::new::<pyo3::exceptions::PyTypeError, _>(format!(
            "Unsupported set element type: {}. Sets can only contain strings, numbers, or bytes",
            first.get_type().name()?
        )));
    }

    Ok(())
}

/// Convert a DynamoDB AttributeValue representation back to a Python object.
///
/// This is the inverse of `py_to_dynamo`. It takes a dict in DynamoDB format
/// and returns the corresponding Python value.
///
/// # Arguments
///
/// * `py` - Python interpreter reference
/// * `attr` - A dict containing a DynamoDB AttributeValue
///
/// # Returns
///
/// The corresponding Python object (str, int, float, bool, list, dict, bytes, set, or None).
///
/// # Errors
///
/// Returns ValueError if the AttributeValue format is unknown.
///
/// # Examples
///
/// ```python
/// from pydynox._rust import dynamo_to_py
///
/// # String
/// result = dynamo_to_py({"S": "hello"})
/// assert result == "hello"
///
/// # Number (int)
/// result = dynamo_to_py({"N": "42"})
/// assert result == 42
///
/// # Number (float)
/// result = dynamo_to_py({"N": "3.14"})
/// assert result == 3.14
///
/// # Boolean
/// result = dynamo_to_py({"BOOL": True})
/// assert result == True
///
/// # Null
/// result = dynamo_to_py({"NULL": True})
/// assert result is None
/// ```
pub fn dynamo_to_py(py: Python<'_>, attr: &Bound<'_, PyDict>) -> PyResult<Py<PyAny>> {
    // String
    if let Some(s) = attr.get_item("S")? {
        return Ok(s.unbind());
    }

    // Number (stored as string, convert to int or float)
    if let Some(n) = attr.get_item("N")? {
        let n_str: String = n.extract()?;
        return parse_number_to_py(py, &n_str);
    }

    // Boolean
    if let Some(b) = attr.get_item("BOOL")? {
        return Ok(b.unbind());
    }

    // Null
    if attr.get_item("NULL")?.is_some() {
        return Ok(py.None());
    }

    // Binary (base64 encoded)
    if let Some(b) = attr.get_item("B")? {
        let b_str: String = b.extract()?;
        let decoded = base64::engine::general_purpose::STANDARD
            .decode(&b_str)
            .map_err(|e| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                    "Invalid base64 encoding: {}",
                    e
                ))
            })?;
        let py_bytes = pyo3::types::PyBytes::new(py, &decoded);
        return Ok(py_bytes.into_any().unbind());
    }

    // List
    if let Some(list) = attr.get_item("L")? {
        let py_list = PyList::empty(py);
        for item in list.cast::<PyList>()?.iter() {
            let dict = item.cast::<PyDict>()?;
            py_list.append(dynamo_to_py(py, dict)?)?;
        }
        return Ok(py_list.unbind().into_any());
    }

    // Map
    if let Some(map) = attr.get_item("M")? {
        let py_dict = PyDict::new(py);
        for (k, v) in map.cast::<PyDict>()?.iter() {
            let dict = v.cast::<PyDict>()?;
            py_dict.set_item(k, dynamo_to_py(py, dict)?)?;
        }
        return Ok(py_dict.unbind().into_any());
    }

    // String Set
    if let Some(ss) = attr.get_item("SS")? {
        let py_set = PySet::empty(py)?;
        for item in ss.cast::<PyList>()?.iter() {
            py_set.add(item)?;
        }
        return Ok(py_set.unbind().into_any());
    }

    // Number Set
    if let Some(ns) = attr.get_item("NS")? {
        let py_set = PySet::empty(py)?;
        for item in ns.cast::<PyList>()?.iter() {
            let n_str: String = item.extract()?;
            let py_num = parse_number_to_py(py, &n_str)?;
            py_set.add(py_num.bind(py))?;
        }
        return Ok(py_set.unbind().into_any());
    }

    // Binary Set
    if let Some(bs) = attr.get_item("BS")? {
        let py_set = PySet::empty(py)?;
        for item in bs.cast::<PyList>()?.iter() {
            let b_str: String = item.extract()?;
            let decoded = base64::engine::general_purpose::STANDARD
                .decode(&b_str)
                .map_err(|e| {
                    PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                        "Invalid base64 encoding: {}",
                        e
                    ))
                })?;
            let py_bytes = pyo3::types::PyBytes::new(py, &decoded);
            py_set.add(py_bytes)?;
        }
        return Ok(py_set.unbind().into_any());
    }

    Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
        "Unknown DynamoDB AttributeValue type. Expected one of: S, N, BOOL, NULL, B, L, M, SS, NS, BS",
    ))
}

/// Python-exposed function to convert a Python value to DynamoDB format.
///
/// This is the main entry point for Python code to serialize values.
///
/// # Arguments
///
/// * `value` - Any Python value to convert
///
/// # Returns
///
/// A dict in DynamoDB AttributeValue format.
#[pyfunction]
#[pyo3(name = "py_to_dynamo")]
pub fn py_to_dynamo_py(py: Python<'_>, value: &Bound<'_, PyAny>) -> PyResult<Py<PyDict>> {
    py_to_dynamo(py, value)
}

/// Python-exposed function to convert a DynamoDB AttributeValue to Python.
///
/// This is the main entry point for Python code to deserialize values.
///
/// # Arguments
///
/// * `attr` - A dict in DynamoDB AttributeValue format
///
/// # Returns
///
/// The corresponding Python value.
#[pyfunction]
#[pyo3(name = "dynamo_to_py")]
pub fn dynamo_to_py_py(py: Python<'_>, attr: &Bound<'_, PyDict>) -> PyResult<Py<PyAny>> {
    dynamo_to_py(py, attr)
}

/// Convert a full Python dict (item) to DynamoDB format.
///
/// Each value in the dict is converted to DynamoDB AttributeValue format.
///
/// # Arguments
///
/// * `item` - A Python dict representing a DynamoDB item
///
/// # Returns
///
/// A dict where each value is in DynamoDB AttributeValue format.
///
/// # Examples
///
/// ```python
/// from pydynox._rust import item_to_dynamo
///
/// item = {"pk": "USER#123", "name": "John", "age": 30}
/// result = item_to_dynamo(item)
/// # result = {
/// #     "pk": {"S": "USER#123"},
/// #     "name": {"S": "John"},
/// #     "age": {"N": "30"}
/// # }
/// ```
#[pyfunction]
pub fn item_to_dynamo(py: Python<'_>, item: &Bound<'_, PyDict>) -> PyResult<Py<PyDict>> {
    let result = PyDict::new(py);
    for (k, v) in item.iter() {
        let key: String = k.extract()?;
        let value = py_to_dynamo(py, &v)?;
        result.set_item(key, value)?;
    }
    Ok(result.unbind())
}

/// Convert a DynamoDB item (dict of AttributeValues) back to a Python dict.
///
/// Each AttributeValue in the dict is converted back to a Python value.
///
/// # Arguments
///
/// * `item` - A dict where each value is in DynamoDB AttributeValue format
///
/// # Returns
///
/// A plain Python dict with native Python values.
///
/// # Examples
///
/// ```python
/// from pydynox._rust import item_from_dynamo
///
/// dynamo_item = {
///     "pk": {"S": "USER#123"},
///     "name": {"S": "John"},
///     "age": {"N": "30"}
/// }
/// result = item_from_dynamo(dynamo_item)
/// # result = {"pk": "USER#123", "name": "John", "age": 30}
/// ```
#[pyfunction]
pub fn item_from_dynamo(py: Python<'_>, item: &Bound<'_, PyDict>) -> PyResult<Py<PyDict>> {
    let result = PyDict::new(py);
    for (k, v) in item.iter() {
        let key: String = k.extract()?;
        let attr = v.cast::<PyDict>()?;
        let value = dynamo_to_py(py, attr)?;
        result.set_item(key, value)?;
    }
    Ok(result.unbind())
}
