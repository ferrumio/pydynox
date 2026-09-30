//! Lease lifecycle, deadlines, renewal, and cancellation.

use std::future::Future;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

use aws_sdk_dynamodb::config::retry::RetryConfig;
use pyo3::exceptions::{PyRuntimeError, PyTypeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::PyDict;
use tokio::runtime::Runtime;
use tokio::sync::{Mutex as AsyncMutex, Notify};
use uuid::Uuid;

use super::clock::Stamp;
use super::store::{Failure, Row};
use super::{ClientState, MemoryLockState, Store, duration, validate_key};
use crate::errors::{ConnectionException, LockLost, LockNotAcquired, LockReleaseError};

/// Per-acquisition metrics. Capacity includes successful responses only.
#[pyclass(from_py_object, get_all)]
#[derive(Clone, Default)]
pub struct LockMetrics {
    read_requests: u64,
    write_requests: u64,
    conditional_failures: u64,
    request_failures: u64,
    wait_timeouts: u64,
    cleanup_failures: u64,
    consumed_rcu: f64,
    consumed_wcu: f64,
    renewals: u64,
    wait_ms: f64,
    lost: bool,
}

#[derive(Clone, Copy, PartialEq)]
enum Phase {
    New,
    Acquiring,
    Held,
    Releasing,
    Released,
    Lost,
    Failed,
}

struct State {
    phase: Phase,
    row: Row,
    stamp: Option<Stamp>,
    reason: String,
    metrics: LockMetrics,
}

struct Inner {
    store: Store,
    observations: Arc<ClientState>,
    runtime: Arc<Runtime>,
    pid: u32,
    table: String,
    key: String,
    lease: Duration,
    wait: Duration,
    state: Mutex<State>,
    io: AsyncMutex<()>,
    stop: AtomicBool,
    may_own: AtomicBool,
    cleanup_started: AtomicBool,
    changed: Notify,
}

impl Inner {
    fn check_pid(&self) -> PyResult<()> {
        if self.pid != std::process::id() {
            return Err(PyRuntimeError::new_err(
                "A lock or client cannot be inherited across fork; create the client in the child",
            ));
        }
        Ok(())
    }

    fn lose(&self, reason: &str) {
        let mut state = self.state.lock().unwrap();
        if matches!(
            state.phase,
            Phase::Held | Phase::Acquiring | Phase::Releasing
        ) {
            state.phase = Phase::Lost;
            state.reason = reason.to_owned();
            state.metrics.lost = true;
            ::tracing::warn!(
                operation = "lock",
                acquisition_id = %state.row.owner,
                state = "lost",
                "Lease ownership lost"
            );
        }
        self.stop.store(true, Ordering::Release);
        self.changed.notify_one();
    }

    fn check_held(&self) -> PyResult<()> {
        self.check_pid()?;
        let expired = {
            let state = self.state.lock().unwrap();
            state.phase == Phase::Held && !state.stamp.is_some_and(|stamp| stamp.valid(self.lease))
        };
        if expired {
            self.lose("The local lease deadline expired");
        }
        let state = self.state.lock().unwrap();
        if state.phase != Phase::Held || self.stop.load(Ordering::Acquire) {
            return Err(LockLost::new_err(if state.reason.is_empty() {
                "The lock is not held".to_owned()
            } else {
                state.reason.clone()
            }));
        }
        Ok(())
    }

    async fn request<T>(
        &self,
        deadline: Instant,
        write: bool,
        operation: impl Future<Output = Result<(T, f64), Failure>>,
    ) -> Result<T, Failure> {
        let remaining = deadline.saturating_duration_since(Instant::now());
        if remaining.is_zero() {
            return Err(Failure::Error(ConnectionException::new_err(
                "Lock request deadline expired",
            )));
        }
        {
            let mut state = self.state.lock().unwrap();
            if write {
                state.metrics.write_requests += 1;
            } else {
                state.metrics.read_requests += 1;
            }
        }
        let timeout = remaining.min(self.lease / 3).min(Duration::from_secs(5));
        let result = tokio::time::timeout(timeout, operation)
            .await
            .unwrap_or_else(|_| {
                Err(Failure::Error(ConnectionException::new_err(
                    "Lock request timed out; its remote outcome may be unknown",
                )))
            });
        let mut state = self.state.lock().unwrap();
        match result {
            Ok((value, capacity)) => {
                if write {
                    state.metrics.consumed_wcu += capacity;
                } else {
                    state.metrics.consumed_rcu += capacity;
                }
                Ok(value)
            }
            Err(error) => {
                if matches!(error, Failure::Contended) {
                    state.metrics.conditional_failures += 1;
                } else {
                    state.metrics.request_failures += 1;
                }
                Err(error)
            }
        }
    }

    fn wait_expired(&self) -> PyErr {
        self.state.lock().unwrap().metrics.wait_timeouts += 1;
        LockNotAcquired::new_err("The lock was not available within the acquisition budget")
    }

    async fn read(&self, deadline: Instant) -> Result<Option<Row>, Failure> {
        self.request(deadline, false, self.store.get(&self.table, &self.key))
            .await
    }

    async fn write(
        &self,
        deadline: Instant,
        row: &Row,
        expected: Option<&Row>,
    ) -> Result<(), Failure> {
        self.may_own.store(true, Ordering::Release);
        let result = self
            .request(deadline, true, async {
                self.store
                    .put(&self.table, &self.key, row, expected)
                    .await
                    .map(|capacity| ((), capacity))
            })
            .await;
        match result {
            Err(Failure::Contended) => {
                self.may_own.store(false, Ordering::Release);
                Err(Failure::Contended)
            }
            Err(error) => {
                // An accepted write may lose its response. Only the exact
                // attempted acquisition/version can confirm this attempt.
                if let Ok(Some(actual)) = self.read(deadline).await
                    && actual.owner == row.owner
                    && actual.version == row.version
                {
                    return Ok(());
                }
                Err(error)
            }
            other => other,
        }
    }

    async fn acquire(self: Arc<Self>) -> PyResult<()> {
        self.check_pid()?;
        {
            let mut state = self.state.lock().unwrap();
            if state.phase != Phase::New {
                return Err(PyRuntimeError::new_err("Lock guards are single-use"));
            }
            state.phase = Phase::Acquiring;
        }
        let mut cancellation = AcquisitionCancellation {
            inner: self.clone(),
            armed: true,
            start: Instant::now(),
        };
        let _io = self.io.lock().await;
        let start = Instant::now();
        // Zero wait is one bounded attempt, not a zero-duration network timeout.
        let budget = if self.wait.is_zero() {
            self.lease.mul_f64(0.6).min(Duration::from_secs(5))
        } else {
            self.wait
        };
        let deadline = start + budget;
        let mut observed: Option<Row> = None;
        loop {
            if self.stop.load(Ordering::Acquire) {
                return Err(LockNotAcquired::new_err("Lock acquisition was cancelled"));
            }
            let row = self.state.lock().unwrap().row.clone();
            let stamp = Stamp::now();
            let write = self.write(deadline, &row, observed.as_ref()).await;
            match write {
                Ok(()) => {
                    if !stamp.valid(self.lease) || Instant::now() >= deadline {
                        return Err(LockLost::new_err(
                            "Acquisition completed after its deadline",
                        ));
                    }
                    {
                        let mut state = self.state.lock().unwrap();
                        if self.stop.load(Ordering::Acquire) || state.phase != Phase::Acquiring {
                            return Err(LockLost::new_err("Lock acquisition was cancelled"));
                        }
                        state.phase = Phase::Held;
                        state.stamp = Some(stamp);
                        state.metrics.wait_ms = start.elapsed().as_secs_f64() * 1000.0;
                    }
                    self.observations.forget(&self.table, &self.key);
                    ::tracing::debug!(
                        operation = "lock",
                        acquisition_id = %row.owner,
                        state = "held",
                        "Lease acquired"
                    );
                    self.runtime.spawn(self.clone().heartbeat());
                    cancellation.armed = false;
                    return Ok(());
                }
                Err(Failure::Error(error)) => return Err(error),
                Err(Failure::Contended) => {}
            }
            // Contention polling uses reads. Only try another write after a
            // missing row or a full unchanged-version observation.
            loop {
                let row = match self.read(deadline).await {
                    Ok(row) => row,
                    Err(Failure::Error(error)) => return Err(error),
                    Err(Failure::Contended) => unreachable!(),
                };
                match row {
                    None => {
                        self.observations.forget(&self.table, &self.key);
                        observed = None;
                        break;
                    }
                    Some(row) => {
                        let since = self.observations.observe(&self.table, &self.key, &row);
                        if since.elapsed() >= row.lease {
                            observed = Some(row);
                            break;
                        }
                    }
                }
                if self.wait.is_zero() || Instant::now() >= deadline {
                    self.state.lock().unwrap().metrics.wait_ms =
                        start.elapsed().as_secs_f64() * 1000.0;
                    return Err(self.wait_expired());
                }
                let poll = (self.lease / 6)
                    .clamp(Duration::from_millis(10), Duration::from_secs(1))
                    .mul_f64(0.8 + rand::random::<f64>() * 0.4)
                    .min(deadline.saturating_duration_since(Instant::now()));
                if tokio::time::timeout(poll, self.changed.notified())
                    .await
                    .is_ok()
                    || self.stop.load(Ordering::Acquire)
                {
                    return Err(LockNotAcquired::new_err("Lock acquisition was cancelled"));
                }
                if Instant::now() >= deadline {
                    return Err(self.wait_expired());
                }
            }
            if Instant::now() >= deadline {
                return Err(self.wait_expired());
            }
        }
    }

    async fn heartbeat(self: Arc<Self>) {
        let mut interval = self.lease / 3;
        loop {
            if tokio::time::timeout(interval, self.changed.notified())
                .await
                .is_ok()
                || self.stop.load(Ordering::Acquire)
            {
                return;
            }
            let _io = self.io.lock().await;
            if self.stop.load(Ordering::Acquire) || self.check_held().is_err() {
                return;
            }
            let (old, old_stamp) = {
                let state = self.state.lock().unwrap();
                (state.row.clone(), state.stamp.unwrap())
            };
            let new = Row {
                version: Uuid::new_v4().to_string(),
                ..old.clone()
            };
            let sent = Stamp::now();
            let deadline = old_stamp.monotonic + self.lease.mul_f64(0.9);
            let result = self
                .request(deadline, true, async {
                    self.store
                        .renew(&self.table, &self.key, &old, &new)
                        .await
                        .map(|capacity| ((), capacity))
                })
                .await;
            if self.stop.load(Ordering::Acquire) {
                return;
            }
            let confirmed = match result {
                Ok(()) => true,
                Err(Failure::Contended) => {
                    self.lose("Another worker owns the lock");
                    return;
                }
                Err(Failure::Error(_)) => matches!(
                    self.read(deadline).await,
                    Ok(Some(actual)) if actual.owner == new.owner && actual.version == new.version
                ),
            };
            if self.stop.load(Ordering::Acquire) {
                return;
            }
            // An old deadline cannot be rescued by a delayed success.
            if !old_stamp.valid(self.lease) || !sent.valid(self.lease) {
                self.lose("Renewal was not confirmed before the lease deadline");
                return;
            }
            if confirmed {
                let mut state = self.state.lock().unwrap();
                if state.phase != Phase::Held {
                    return;
                }
                state.row = new;
                state.stamp = Some(sent);
                state.metrics.renewals += 1;
                interval = self.lease / 3;
            } else {
                // Retry inside the existing deadline, never extend on failure.
                interval = (self.lease / 12).min(Duration::from_secs(1));
            }
        }
    }

    fn cancel(self: &Arc<Self>) {
        if self.pid != std::process::id() {
            return;
        }
        self.stop.store(true, Ordering::Release);
        self.changed.notify_one();
        {
            let mut state = self.state.lock().unwrap();
            match state.phase {
                Phase::Held => {
                    state.phase = Phase::Lost;
                    state.metrics.lost = true;
                    state.reason = "Lock guard was cancelled".into();
                }
                Phase::New | Phase::Acquiring => state.phase = Phase::Failed,
                _ => {}
            }
        }
        if self.may_own.load(Ordering::Acquire)
            && !self.cleanup_started.swap(true, Ordering::AcqRel)
        {
            let inner = self.clone();
            self.runtime.spawn(async move {
                if inner.cleanup().await.is_err() {
                    ::tracing::warn!(operation = "lock", "Cancelled lock cleanup failed");
                }
            });
        }
    }

    async fn cleanup(&self) -> PyResult<()> {
        // Include an in-flight acquisition/renewal in the cleanup budget.
        let deadline = Instant::now() + self.lease.mul_f64(0.6).min(Duration::from_secs(10));
        let _io = tokio::time::timeout_at(deadline.into(), self.io.lock())
            .await
            .map_err(|_| {
                self.state.lock().unwrap().metrics.cleanup_failures += 1;
                LockReleaseError::new_err("Lock cleanup timed out waiting for an in-flight request")
            })?;
        if !self.may_own.load(Ordering::Acquire) {
            return Ok(());
        }
        let owner = self.state.lock().unwrap().row.owner.clone();
        // Reserve a second request window to reconcile a lost delete response.
        let result = self
            .request(deadline, true, async {
                self.store
                    .delete(&self.table, &self.key, &owner)
                    .await
                    .map(|capacity| ((), capacity))
            })
            .await;
        self.may_own.store(false, Ordering::Release);
        match result {
            Ok(()) => Ok(()),
            Err(Failure::Contended) => {
                self.state.lock().unwrap().metrics.cleanup_failures += 1;
                self.lose("Lock release no longer matches this acquisition");
                Err(LockLost::new_err(
                    "Lock release no longer matches this acquisition",
                ))
            }
            Err(Failure::Error(_error)) => {
                if matches!(self.read(deadline).await, Ok(None)) {
                    return Ok(());
                }
                self.state.lock().unwrap().metrics.cleanup_failures += 1;
                // Formatting a PyErr would acquire the GIL on a background
                // runtime thread and can block unrelated synchronous requests.
                Err(LockReleaseError::new_err(
                    "Lock release could not be confirmed; the row may remain until recovery",
                ))
            }
        }
    }

    async fn release(self: Arc<Self>) -> PyResult<()> {
        self.check_pid()?;
        let lost = self.check_held().err();
        {
            let mut state = self.state.lock().unwrap();
            if matches!(state.phase, Phase::Released | Phase::Releasing) {
                return Err(PyRuntimeError::new_err("Lock guard already released"));
            }
            if lost.is_none() {
                state.phase = Phase::Releasing;
            }
        }
        self.stop.store(true, Ordering::Release);
        self.changed.notify_one();
        self.cleanup_started.store(true, Ordering::Release);
        let cleanup = self.cleanup().await;
        if let Some(error) = lost {
            return Err(error);
        }
        cleanup?;
        let mut state = self.state.lock().unwrap();
        state.phase = Phase::Released;
        ::tracing::debug!(
            operation = "lock",
            acquisition_id = %state.row.owner,
            state = "released",
            "Lease released"
        );
        Ok(())
    }
}

struct AcquisitionCancellation {
    inner: Arc<Inner>,
    armed: bool,
    start: Instant,
}

impl Drop for AcquisitionCancellation {
    fn drop(&mut self) {
        self.inner.state.lock().unwrap().metrics.wait_ms =
            self.start.elapsed().as_secs_f64() * 1000.0;
        if self.armed {
            self.inner.cancel();
        }
    }
}

/// Internal guard; Python only supplies API and context-manager glue.
#[pyclass]
pub struct NativeLease {
    inner: Arc<Inner>,
}

#[pymethods]
impl NativeLease {
    #[new]
    #[pyo3(signature = (backend, table, key, lease_duration=30.0, wait_timeout=35.0))]
    fn new(
        backend: &Bound<'_, PyAny>,
        table: String,
        key: String,
        lease_duration: f64,
        wait_timeout: f64,
    ) -> PyResult<Self> {
        validate_key(&key)?;
        if table.is_empty() {
            return Err(PyValueError::new_err("Lock table must not be empty"));
        }
        let lease = duration(lease_duration, "lease_duration", false)?;
        let wait = duration(wait_timeout, "wait_timeout", true)?;
        let (store, observations, pid) =
            if let Ok(client) = backend.extract::<PyRef<'_, crate::client::DynamoDBClient>>() {
                if client.process_id != std::process::id() {
                    return Err(PyRuntimeError::new_err(
                        "Create the DynamoDB client after fork",
                    ));
                }
                let sdk = client.lock_client.get_or_init(|| {
                    let config = client
                        .client
                        .config()
                        .to_builder()
                        .retry_config(RetryConfig::standard().with_max_attempts(1))
                        .build();
                    aws_sdk_dynamodb::Client::from_conf(config)
                });
                (
                    Store::Aws(sdk.clone()),
                    client.lock_state.clone(),
                    client.process_id,
                )
            } else if let Ok(state) = backend.getattr("_lock_state") {
                let state = state.extract::<PyRef<'_, MemoryLockState>>()?;
                (
                    Store::Memory(Arc::new(backend.clone().unbind())),
                    state.state.clone(),
                    state.pid,
                )
            } else {
                return Err(PyTypeError::new_err("Unsupported distributed lock client"));
            };
        if pid != std::process::id() {
            return Err(PyRuntimeError::new_err(
                "Create the DynamoDB client after fork",
            ));
        }
        let inner = Arc::new(Inner {
            store,
            observations,
            runtime: crate::runtime::get_runtime()?,
            pid,
            table,
            key,
            lease,
            wait,
            state: Mutex::new(State {
                phase: Phase::New,
                row: Row {
                    owner: Uuid::new_v4().to_string(),
                    version: Uuid::new_v4().to_string(),
                    lease,
                },
                stamp: None,
                reason: String::new(),
                metrics: LockMetrics::default(),
            }),
            io: AsyncMutex::new(()),
            stop: AtomicBool::new(false),
            may_own: AtomicBool::new(false),
            cleanup_started: AtomicBool::new(false),
            changed: Notify::new(),
        });
        Ok(Self { inner })
    }

    fn acquire<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        self.inner.check_pid()?;
        let inner = self.inner.clone();
        pyo3_async_runtimes::tokio::future_into_py(py, inner.acquire())
    }

    fn sync_acquire(&self, py: Python<'_>) -> PyResult<()> {
        self.inner.check_pid()?;
        let inner = self.inner.clone();
        py.detach(|| self.inner.runtime.block_on(inner.acquire()))
    }

    fn release<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        self.inner.check_pid()?;
        let inner = self.inner.clone();
        // Cleanup is independent of cancellation of the awaiting Python task.
        let task = self.inner.runtime.spawn(inner.release());
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            task.await
                .map_err(|error| PyRuntimeError::new_err(error.to_string()))?
        })
    }

    fn sync_release(&self, py: Python<'_>) -> PyResult<()> {
        self.inner.check_pid()?;
        let inner = self.inner.clone();
        py.detach(|| self.inner.runtime.block_on(inner.release()))
    }

    fn cancel(&self) {
        self.inner.cancel();
    }

    fn raise_if_lost(&self) -> PyResult<()> {
        self.inner.check_held()
    }

    #[getter]
    fn metrics(&self) -> PyResult<LockMetrics> {
        self.inner.check_pid()?;
        Ok(self.inner.state.lock().unwrap().metrics.clone())
    }

    fn condition_check<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyDict>> {
        self.inner.check_held()?;
        let owner = self.inner.state.lock().unwrap().row.owner.clone();
        let result = PyDict::new(py);
        let key = PyDict::new(py);
        key.set_item("key", &self.inner.key)?;
        let names = PyDict::new(py);
        names.set_item("#owner", "owner")?;
        let values = PyDict::new(py);
        values.set_item(":owner", owner)?;
        result.set_item("table", &self.inner.table)?;
        result.set_item("key", key)?;
        result.set_item("condition_expression", "#owner = :owner")?;
        result.set_item("expression_attribute_names", names)?;
        result.set_item("expression_attribute_values", values)?;
        Ok(result)
    }
}

impl Drop for NativeLease {
    fn drop(&mut self) {
        self.inner.cancel();
    }
}
