//! Cooperative distributed leases. Production operations stay in Rust.

mod clock;
mod key;
mod lease;
mod store;

use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

use store::Store;

#[derive(Clone)]
struct Observation {
    owner: String,
    version: String,
    lease: Duration,
    since: Instant,
}

/// Per-client observations allow repeated short attempts to discover abandonment.
#[derive(Default)]
pub(crate) struct ClientState {
    observations: Mutex<HashMap<(String, String), Observation>>,
}

impl ClientState {
    fn observe(&self, table: &str, key: &str, row: &store::Row) -> Instant {
        let mut observations = self.observations.lock().unwrap();
        let identity = (table.to_owned(), key.to_owned());
        if let Some(old) = observations.get(&identity)
            && old.owner == row.owner
            && old.version == row.version
            && old.lease == row.lease
        {
            return old.since;
        }
        // Eviction only delays takeover; it must never make a lock expire sooner.
        if observations.len() >= 4096 {
            observations.clear();
        }
        let since = Instant::now();
        observations.insert(
            identity,
            Observation {
                owner: row.owner.clone(),
                version: row.version.clone(),
                lease: row.lease,
                since,
            },
        );
        since
    }

    fn forget(&self, table: &str, key: &str) {
        self.observations
            .lock()
            .unwrap()
            .remove(&(table.to_owned(), key.to_owned()));
    }
}

/// Opaque state shared by clients of the Python memory backend.
#[pyclass]
pub(crate) struct MemoryLockState {
    state: Arc<ClientState>,
    pid: u32,
}

#[pymethods]
impl MemoryLockState {
    #[new]
    fn new() -> Self {
        Self {
            state: Arc::new(ClientState::default()),
            pid: std::process::id(),
        }
    }
}

pub(crate) fn duration(value: f64, name: &str, zero: bool) -> PyResult<Duration> {
    let minimum = if zero { 0.0 } else { 0.1 };
    if !value.is_finite() || !(minimum..=86_400.0).contains(&value) {
        return Err(PyValueError::new_err(format!(
            "{name} must be finite and between {minimum} and 86400 seconds"
        )));
    }
    Ok(Duration::from_secs_f64(value))
}

pub(crate) fn validate_key(key: &str) -> PyResult<()> {
    if key.is_empty() || key.len() > 2048 {
        return Err(PyValueError::new_err(
            "Lock key must contain between 1 and 2048 UTF-8 bytes",
        ));
    }
    Ok(())
}

/// Install internal bindings. Python's lock module is the public interface.
pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<lease::NativeLease>()?;
    m.add_class::<lease::LockMetrics>()?;
    m.add_class::<key::LockKeyTemplate>()?;
    m.add_class::<MemoryLockState>()?;
    Ok(())
}
