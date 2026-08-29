//! Operation metrics for observability.
//!
//! This module provides metrics from DynamoDB operations including
//! duration, consumed capacity, and request IDs.

use aws_sdk_dynamodb::types::ConsumedCapacity;
use pyo3::prelude::*;

/// Metrics returned from DynamoDB operations.
///
/// Contains timing, capacity consumption, and request tracking info.
/// All fields except duration_ms are optional since DynamoDB may not
/// return them depending on the operation and settings.
#[pyclass(from_py_object)]
#[derive(Clone, Debug, Default)]
pub struct OperationMetrics {
    /// Operation duration in milliseconds.
    #[pyo3(get)]
    pub duration_ms: f64,

    /// Read capacity units consumed (if ReturnConsumedCapacity was set).
    #[pyo3(get)]
    pub consumed_rcu: Option<f64>,

    /// Write capacity units consumed (if ReturnConsumedCapacity was set).
    #[pyo3(get)]
    pub consumed_wcu: Option<f64>,

    /// AWS request ID for debugging.
    #[pyo3(get)]
    pub request_id: Option<String>,

    /// Number of items returned (for query/scan operations).
    #[pyo3(get)]
    pub items_count: Option<usize>,

    /// Number of items scanned before filtering.
    #[pyo3(get)]
    pub scanned_count: Option<usize>,

    /// Vector search request bytes consumed.
    #[pyo3(get)]
    pub vector_search_bytes: Option<f64>,

    /// Vector write request bytes consumed.
    #[pyo3(get)]
    pub vector_write_bytes: Option<f64>,
}

#[pymethods]
impl OperationMetrics {
    /// Create new metrics with just duration.
    #[new]
    #[pyo3(signature = (duration_ms=0.0))]
    pub fn new(duration_ms: f64) -> Self {
        Self {
            duration_ms,
            ..Default::default()
        }
    }

    fn __repr__(&self) -> String {
        let mut parts = vec![format!("duration_ms={:.2}", self.duration_ms)];

        if let Some(rcu) = self.consumed_rcu {
            parts.push(format!("rcu={:.1}", rcu));
        }
        if let Some(wcu) = self.consumed_wcu {
            parts.push(format!("wcu={:.1}", wcu));
        }
        if let Some(count) = self.items_count {
            parts.push(format!("items={}", count));
        }
        if let Some(bytes) = self.vector_search_bytes {
            parts.push(format!("vector_search_bytes={:.0}", bytes));
        }
        if let Some(bytes) = self.vector_write_bytes {
            parts.push(format!("vector_write_bytes={:.0}", bytes));
        }
        if let Some(ref req_id) = self.request_id {
            // Truncate request_id for readability
            let short_id = if req_id.len() > 8 {
                format!("{}...", &req_id[..8])
            } else {
                req_id.clone()
            };
            parts.push(format!("request_id={}", short_id));
        }

        format!("OperationMetrics({})", parts.join(", "))
    }
}

/// Sum vector write request bytes across all vector indexes.
pub fn vector_write_bytes(capacity: Option<&ConsumedCapacity>) -> Option<f64> {
    let total = capacity
        .and_then(|value| value.vector_indexes())
        .map(|indexes| {
            indexes
                .values()
                .filter_map(|value| value.vector_write_request_bytes())
                .sum::<f64>()
        })?;
    Some(total)
}

impl OperationMetrics {
    /// Create metrics with all fields.
    pub fn with_capacity(
        duration_ms: f64,
        consumed_rcu: Option<f64>,
        consumed_wcu: Option<f64>,
        request_id: Option<String>,
    ) -> Self {
        Self {
            duration_ms,
            consumed_rcu,
            consumed_wcu,
            request_id,
            items_count: None,
            scanned_count: None,
            vector_search_bytes: None,
            vector_write_bytes: None,
        }
    }

    /// Set items count (for query/scan).
    pub fn with_items_count(mut self, count: usize) -> Self {
        self.items_count = Some(count);
        self
    }

    /// Set scanned count (for query/scan).
    pub fn with_scanned_count(mut self, count: usize) -> Self {
        self.scanned_count = Some(count);
        self
    }

    /// Set vector capacity metrics.
    pub fn with_vector_capacity(
        mut self,
        search_bytes: Option<f64>,
        write_bytes: Option<f64>,
    ) -> Self {
        self.vector_search_bytes = search_bytes;
        self.vector_write_bytes = write_bytes;
        self
    }
}

/// Register metrics class in Python module.
pub fn register_metrics(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<OperationMetrics>()?;
    Ok(())
}
