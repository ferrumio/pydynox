//! Shared Tokio runtime used by all pydynox clients.

use once_cell::sync::Lazy;
use pyo3::prelude::*;
use std::sync::Arc;
use tokio::runtime::Runtime;

static RUNTIME: Lazy<Result<Arc<Runtime>, String>> = Lazy::new(|| {
    Runtime::new().map(Arc::new).map_err(|e| {
        format!(
            "Failed to create Tokio runtime: {}. \
             This can happen in sandboxed environments with strict thread limits.",
            e
        )
    })
});

/// Get the shared Tokio runtime.
///
/// Returns a PyRuntimeError if runtime initialization failed (e.g., in sandboxed
/// environments with strict thread limits, or when the process has exhausted
/// system resources).
pub fn get_runtime() -> PyResult<Arc<Runtime>> {
    RUNTIME
        .as_ref()
        .map(Arc::clone)
        .map_err(|msg| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(msg.as_str()))
}
