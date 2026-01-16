//! LSI (Local Secondary Index) definitions and parsing.
//!
//! LSIs share the table's hash key but have a different sort key.
//! They must be created with the table (cannot be added later).

use pyo3::prelude::*;
use pyo3::types::PyList;

use crate::errors::ValidationException;

/// LSI definition from Python.
#[derive(Debug)]
pub struct LsiDefinition {
    pub index_name: String,
    /// Range key attribute (name, type)
    pub range_key_name: String,
    pub range_key_type: String,
    pub projection: String,
    pub non_key_attributes: Option<Vec<String>>,
}

/// Parse LSI definitions from Python list.
///
/// Format:
/// ```python
/// {
///     "index_name": "status-index",
///     "range_key": ("status", "S"),
///     "projection": "ALL",  # optional, defaults to "ALL"
///     "non_key_attributes": ["email", "name"],  # optional, for INCLUDE projection
/// }
/// ```
pub fn parse_lsi_definitions(
    _py: Python<'_>,
    lsis: &Bound<'_, PyList>,
) -> PyResult<Vec<LsiDefinition>> {
    let mut result = Vec::new();

    for item in lsis.iter() {
        let dict = item.cast::<pyo3::types::PyDict>()?;

        let index_name: String = dict
            .get_item("index_name")?
            .ok_or_else(|| ValidationException::new_err("LSI missing 'index_name'"))?
            .extract()?;

        // Range key is required for LSI
        let range_key = dict
            .get_item("range_key")?
            .ok_or_else(|| ValidationException::new_err("LSI missing 'range_key'"))?;

        let (range_key_name, range_key_type): (String, String) = range_key.extract()?;

        // projection defaults to "ALL"
        let projection: String = dict
            .get_item("projection")?
            .map(|v| v.extract())
            .transpose()?
            .unwrap_or_else(|| "ALL".to_string());

        // non_key_attributes for INCLUDE projection
        let non_key_attributes: Option<Vec<String>> = dict
            .get_item("non_key_attributes")?
            .map(|v| v.extract())
            .transpose()?;

        result.push(LsiDefinition {
            index_name,
            range_key_name,
            range_key_type,
            projection,
            non_key_attributes,
        });
    }

    Ok(result)
}
