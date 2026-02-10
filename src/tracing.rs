//! Tracing and SDK debug logging.
//!
//! Enables AWS SDK debug logs via RUST_LOG env var or programmatically.

use once_cell::sync::OnceCell;
use pyo3::prelude::*;
use tracing_subscriber::EnvFilter;

static TRACING_INITIALIZED: OnceCell<()> = OnceCell::new();

/// Initialize tracing subscriber for SDK debug logs.
///
/// Reads from RUST_LOG env var. Examples:
/// - RUST_LOG=pydynox=debug
/// - RUST_LOG=aws_sdk=debug
/// - RUST_LOG=pydynox=debug,aws_sdk=debug
///
/// Only initializes once. Subsequent calls are no-ops.
fn init_tracing() {
    TRACING_INITIALIZED.get_or_init(|| {
        let filter = EnvFilter::try_from_default_env().unwrap_or_else(|_| EnvFilter::new("warn"));

        tracing_subscriber::fmt()
            .with_env_filter(filter)
            .with_target(true)
            .with_thread_ids(false)
            .with_file(false)
            .with_line_number(false)
            .init();
    });
}

/// Enable SDK debug logging.
///
/// Call this to enable AWS SDK debug logs. Uses RUST_LOG env var
/// or defaults to showing detailed AWS SDK logs.
///
/// # Example
///
/// ```python
/// from pydynox import enable_sdk_debug
/// enable_sdk_debug()  # Uses RUST_LOG env var
///
/// # Or set env var before running:
/// # RUST_LOG=aws_sdk_dynamodb=trace python app.py
/// ```
#[pyfunction]
pub fn enable_sdk_debug() {
    // Set default if RUST_LOG not set
    // Use trace level for maximum detail (HTTP bodies, retries, etc)
    if std::env::var("RUST_LOG").is_err() {
        // SAFETY: called once during tracing setup, before async runtime is active
        unsafe {
            std::env::set_var(
                "RUST_LOG",
                "aws_sdk_dynamodb=trace,aws_smithy_runtime=trace,aws_smithy_http_client=trace,aws_config=debug",
            );
        }
    }
    init_tracing();
}

/// Register tracing functions in Python module.
pub fn register_tracing(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(enable_sdk_debug, m)?)?;
    Ok(())
}
