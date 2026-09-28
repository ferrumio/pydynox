//! Exact decimal conversion without an intermediate binary float.

use pyo3::exceptions::{PyTypeError, PyValueError};
use pyo3::prelude::*;
use pyo3::sync::PyOnceLock;
use pyo3::types::{PyBool, PyInt, PyType};

static DECIMAL_TYPE: PyOnceLock<Py<PyType>> = PyOnceLock::new();

fn decimal_type(py: Python<'_>) -> PyResult<&Bound<'_, PyType>> {
    Ok(DECIMAL_TYPE
        .get_or_try_init(py, || {
            py.import("decimal")?
                .getattr("Decimal")?
                .cast_into::<PyType>()
                .map(Bound::unbind)
                .map_err(PyErr::from)
        })?
        .bind(py))
}

/// Check the Python decimal type only after the primitive fast paths.
pub fn is_decimal(value: &Bound<'_, PyAny>) -> PyResult<bool> {
    value.is_instance(decimal_type(value.py())?)
}

/// Construct Decimal from the original DynamoDB number text.
///
/// Decimal construction does not round to the current arithmetic context.
pub fn from_number_string(py: Python<'_>, value: &str) -> PyResult<Py<PyAny>> {
    Ok(decimal_type(py)?.call1((value,))?.unbind())
}

/// Validate a Decimal and return an exact, normalized DynamoDB number.
///
/// DynamoDB supports up to 38 significant digits, with nonzero magnitudes
/// from 1E-130 through 9.999...E+125. Removing trailing zeros is exact.
pub fn to_number_string(value: &Bound<'_, PyAny>) -> PyResult<String> {
    let text = value.str()?;
    let text = text.to_str()?;
    let negative = text.starts_with('-');
    let unsigned = text.trim_start_matches(['-', '+']);
    let (coefficient, exponent) = match unsigned.split_once(['E', 'e']) {
        Some((coefficient, exponent)) => (
            coefficient,
            exponent
                .parse::<i64>()
                .map_err(|_| PyValueError::new_err("Decimal exponent is out of range"))?,
        ),
        None => (unsigned, 0),
    };
    let decimal_position = coefficient.find('.').unwrap_or(coefficient.len());
    let digits: String = coefficient.chars().filter(|&c| c != '.').collect();
    if digits.is_empty() || !digits.bytes().all(|c| c.is_ascii_digit()) {
        return Err(PyValueError::new_err("Decimal must be finite"));
    }

    let Some(first) = digits.find(|c| c != '0') else {
        return Ok("0".to_string());
    };
    let last = digits.rfind(|c| c != '0').unwrap_or(first);
    let significant = &digits[first..=last];
    if significant.len() > 38 {
        return Err(PyValueError::new_err(
            "Decimal exceeds DynamoDB's 38 significant digits of precision",
        ));
    }
    let adjusted = exponent
        .checked_add(decimal_position as i64 - first as i64 - 1)
        .ok_or_else(|| PyValueError::new_err("Decimal exponent is out of range"))?;
    if !(-130..=125).contains(&adjusted) {
        return Err(PyValueError::new_err(
            "Decimal magnitude must be between 1E-130 and 9.9999999999999999999999999999999999999E+125",
        ));
    }
    let scale = adjusted - significant.len() as i64 + 1;
    let sign = if negative { "-" } else { "" };
    if scale == 0 {
        Ok(format!("{sign}{significant}"))
    } else {
        Ok(format!("{sign}{significant}E{scale}"))
    }
}

/// Validate and coerce a DecimalAttribute value without accepting floats.
#[pyfunction]
pub fn validate_decimal(py: Python<'_>, value: &Bound<'_, PyAny>) -> PyResult<Py<PyAny>> {
    if value.is_none() {
        return Ok(py.None());
    }
    let decimal = if is_decimal(value)? {
        value.clone()
    } else if value.is_instance_of::<PyInt>() && !value.is_instance_of::<PyBool>() {
        decimal_type(py)?.call1((value,))?
    } else {
        return Err(PyTypeError::new_err(
            "DecimalAttribute requires Decimal or int; use Decimal('1.23') for fractional values",
        ));
    };
    to_number_string(&decimal)?;
    Ok(decimal.unbind())
}

/// Match the default numeric decoding for values stored by MemoryBackend.
#[pyfunction]
pub fn decimal_to_number(py: Python<'_>, value: &Bound<'_, PyAny>) -> PyResult<Py<PyAny>> {
    if is_decimal(value)? {
        crate::conversions::parse_number_to_py(py, value.str()?.to_str()?)
    } else {
        Ok(value.clone().unbind())
    }
}
