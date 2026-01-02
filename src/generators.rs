//! Auto-generate strategies for attribute values.
//!
//! Provides fast ID and timestamp generation in Rust.
//! These run on every save when an attribute has an auto-generate strategy.

use chrono::Utc;
use pyo3::prelude::*;
use svix_ksuid::{Ksuid, KsuidLike};
use ulid::Ulid;
use uuid::Uuid;

/// Generate a UUID v4 string.
///
/// Returns a random UUID in standard format.
///
/// # Example output
/// `"550e8400-e29b-41d4-a716-446655440000"`
#[pyfunction]
pub fn generate_uuid4() -> String {
    Uuid::new_v4().to_string()
}

/// Generate a ULID string.
///
/// ULID = Universally Unique Lexicographically Sortable Identifier.
/// 26 characters, Crockford Base32 encoded. Sortable by time.
///
/// # Example output
/// `"01ARZ3NDEKTSV4RRFFQ69G5FAV"`
#[pyfunction]
pub fn generate_ulid() -> String {
    Ulid::new().to_string()
}

/// Generate a KSUID string.
///
/// KSUID = K-Sortable Unique Identifier.
/// 27 characters, base62 encoded. Sortable by time.
///
/// # Example output
/// `"0ujsswThIGTUYm2K8FjOOfXtY1K"`
#[pyfunction]
pub fn generate_ksuid() -> String {
    Ksuid::new(None, None).to_string()
}

/// Generate Unix epoch timestamp in seconds.
///
/// Returns current UTC time as integer seconds since 1970-01-01.
///
/// # Example output
/// `1704067200`
#[pyfunction]
pub fn generate_epoch() -> i64 {
    Utc::now().timestamp()
}

/// Generate Unix epoch timestamp in milliseconds.
///
/// Returns current UTC time as integer milliseconds since 1970-01-01.
///
/// # Example output
/// `1704067200000`
#[pyfunction]
pub fn generate_epoch_ms() -> i64 {
    Utc::now().timestamp_millis()
}

/// Generate ISO 8601 timestamp string.
///
/// Returns current UTC time in ISO 8601 format.
///
/// # Example output
/// `"2024-01-01T00:00:00Z"`
#[pyfunction]
pub fn generate_iso8601() -> String {
    Utc::now().format("%Y-%m-%dT%H:%M:%SZ").to_string()
}

/// Register generator functions with Python module.
pub fn register_generators(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(generate_uuid4, m)?)?;
    m.add_function(wrap_pyfunction!(generate_ulid, m)?)?;
    m.add_function(wrap_pyfunction!(generate_ksuid, m)?)?;
    m.add_function(wrap_pyfunction!(generate_epoch, m)?)?;
    m.add_function(wrap_pyfunction!(generate_epoch_ms, m)?)?;
    m.add_function(wrap_pyfunction!(generate_iso8601, m)?)?;
    Ok(())
}
