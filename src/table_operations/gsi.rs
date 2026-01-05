//! GSI (Global Secondary Index) definitions and parsing.
//!
//! Supports multi-attribute composite keys for GSIs (up to 4 attributes per key).
//! See: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/GSI.DesignPattern.MultiAttributeKeys.html

use pyo3::prelude::*;
use pyo3::types::PyList;

use crate::errors::ValidationError;

/// GSI key attribute (name, type).
#[derive(Debug, Clone)]
pub struct GsiKeyAttribute {
    pub name: String,
    pub attr_type: String,
}

/// GSI definition from Python.
///
/// Supports multi-attribute composite keys for GSIs (up to 4 attributes per key).
#[derive(Debug)]
pub struct GsiDefinition {
    pub index_name: String,
    /// Hash key attributes (1-4 attributes)
    pub hash_keys: Vec<GsiKeyAttribute>,
    /// Range key attributes (0-4 attributes)
    pub range_keys: Vec<GsiKeyAttribute>,
    pub projection: String,
    pub non_key_attributes: Option<Vec<String>>,
}

/// Parse GSI definitions from Python list.
///
/// Accepts both single-attribute keys (backward compatible) and multi-attribute keys.
///
/// Single-attribute format:
/// ```python
/// {
///     "index_name": "email-index",
///     "hash_key": ("email", "S"),
///     "range_key": ("created_at", "S"),  # optional
/// }
/// ```
///
/// Multi-attribute format:
/// ```python
/// {
///     "index_name": "location-index",
///     "hash_keys": [("tenant_id", "S"), ("region", "S")],
///     "range_keys": [("created_at", "S"), ("id", "S")],  # optional
/// }
/// ```
pub fn parse_gsi_definitions(
    _py: Python<'_>,
    gsis: &Bound<'_, PyList>,
) -> PyResult<Vec<GsiDefinition>> {
    let mut result = Vec::new();

    for item in gsis.iter() {
        let dict = item.cast::<pyo3::types::PyDict>()?;

        let index_name: String = dict
            .get_item("index_name")?
            .ok_or_else(|| ValidationError::new_err("GSI missing 'index_name'"))?
            .extract()?;

        // Try multi-attribute format first (hash_keys), then fall back to single (hash_key)
        let hash_keys = if let Some(keys) = dict.get_item("hash_keys")? {
            parse_key_attributes(&keys, "hash_keys")?
        } else if let Some(key) = dict.get_item("hash_key")? {
            // Single attribute format: tuple (name, type)
            let (name, attr_type): (String, String) = key.extract()?;
            vec![GsiKeyAttribute { name, attr_type }]
        } else {
            return Err(ValidationError::new_err(
                "GSI missing 'hash_key' or 'hash_keys'",
            ));
        };

        // Validate hash key count (1-4)
        if hash_keys.is_empty() || hash_keys.len() > 4 {
            return Err(ValidationError::new_err(format!(
                "GSI '{}': hash_keys must have 1-4 attributes, got {}",
                index_name,
                hash_keys.len()
            )));
        }

        // Try multi-attribute format first (range_keys), then fall back to single (range_key)
        let range_keys = if let Some(keys) = dict.get_item("range_keys")? {
            parse_key_attributes(&keys, "range_keys")?
        } else if let Some(key) = dict.get_item("range_key")? {
            // Single attribute format: tuple (name, type)
            let (name, attr_type): (String, String) = key.extract()?;
            vec![GsiKeyAttribute { name, attr_type }]
        } else {
            vec![] // No range key
        };

        // Validate range key count (0-4)
        if range_keys.len() > 4 {
            return Err(ValidationError::new_err(format!(
                "GSI '{}': range_keys must have 0-4 attributes, got {}",
                index_name,
                range_keys.len()
            )));
        }

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

        result.push(GsiDefinition {
            index_name,
            hash_keys,
            range_keys,
            projection,
            non_key_attributes,
        });
    }

    Ok(result)
}

/// Parse key attributes from a Python list of tuples.
fn parse_key_attributes(
    obj: &Bound<'_, PyAny>,
    field_name: &str,
) -> PyResult<Vec<GsiKeyAttribute>> {
    let list: Vec<(String, String)> = obj.extract().map_err(|_| {
        ValidationError::new_err(format!(
            "'{}' must be a list of tuples: [(name, type), ...]",
            field_name
        ))
    })?;

    Ok(list
        .into_iter()
        .map(|(name, attr_type)| GsiKeyAttribute { name, attr_type })
        .collect())
}
