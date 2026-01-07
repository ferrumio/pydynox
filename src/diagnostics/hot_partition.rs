//! Hot partition detection for DynamoDB.
//!
//! Tracks partition key access patterns and warns when a single partition
//! receives too much traffic. Each DynamoDB partition handles ~1000 WCU/s
//! and ~3000 RCU/s. Exceeding these limits causes throttling.
//!
//! This module uses a sliding window counter to track access per partition key.

use pyo3::prelude::*;
use std::collections::HashMap;
use std::sync::Mutex;
use std::time::{Duration, Instant};

/// Entry for tracking access to a partition key.
struct AccessEntry {
    /// Timestamps of write operations within the window.
    writes: Vec<Instant>,
    /// Timestamps of read operations within the window.
    reads: Vec<Instant>,
}

impl AccessEntry {
    fn new() -> Self {
        Self {
            writes: Vec::new(),
            reads: Vec::new(),
        }
    }

    /// Remove entries older than the window duration.
    fn cleanup(&mut self, window: Duration) {
        let cutoff = Instant::now() - window;
        self.writes.retain(|t| *t > cutoff);
        self.reads.retain(|t| *t > cutoff);
    }

    /// Check if entry is empty (can be removed).
    fn is_empty(&self) -> bool {
        self.writes.is_empty() && self.reads.is_empty()
    }
}

/// Hot partition detector that tracks partition key access patterns.
///
/// Uses a sliding window to count reads and writes per partition key.
/// When thresholds are exceeded, returns a warning message.
#[pyclass]
pub struct HotPartitionTracker {
    /// Map of table:pk -> access entry
    entries: Mutex<HashMap<String, AccessEntry>>,
    /// Sliding window duration
    window: Duration,
    /// Write threshold (operations per window)
    writes_threshold: u32,
    /// Read threshold (operations per window)
    reads_threshold: u32,
    /// Last cleanup time
    last_cleanup: Mutex<Instant>,
}

#[pymethods]
impl HotPartitionTracker {
    /// Create a new hot partition tracker.
    ///
    /// # Arguments
    ///
    /// * `writes_threshold` - Max writes per window before warning
    /// * `reads_threshold` - Max reads per window before warning
    /// * `window_seconds` - Sliding window in seconds
    #[new]
    pub fn new(writes_threshold: u32, reads_threshold: u32, window_seconds: u64) -> Self {
        Self {
            entries: Mutex::new(HashMap::new()),
            window: Duration::from_secs(window_seconds),
            writes_threshold,
            reads_threshold,
            last_cleanup: Mutex::new(Instant::now()),
        }
    }

    /// Record a write operation and check for hot partition.
    ///
    /// Returns a warning message if threshold exceeded, None otherwise.
    pub fn record_write(&self, table: &str, pk: &str) -> Option<String> {
        self.maybe_cleanup();

        let key = format!("{}:{}", table, pk);
        let mut entries = self.entries.lock().unwrap();
        let entry = entries.entry(key).or_insert_with(AccessEntry::new);

        entry.writes.push(Instant::now());
        entry.cleanup(self.window);

        let count = entry.writes.len() as u32;
        if count >= self.writes_threshold {
            Some(format!(
                "Hot partition detected - table=\"{}\" pk=\"{}\" had {} writes in {}s",
                table,
                pk,
                count,
                self.window.as_secs()
            ))
        } else {
            None
        }
    }

    /// Record a read operation and check for hot partition.
    ///
    /// Returns a warning message if threshold exceeded, None otherwise.
    pub fn record_read(&self, table: &str, pk: &str) -> Option<String> {
        self.maybe_cleanup();

        let key = format!("{}:{}", table, pk);
        let mut entries = self.entries.lock().unwrap();
        let entry = entries.entry(key).or_insert_with(AccessEntry::new);

        entry.reads.push(Instant::now());
        entry.cleanup(self.window);

        let count = entry.reads.len() as u32;
        if count >= self.reads_threshold {
            Some(format!(
                "Hot partition detected - table=\"{}\" pk=\"{}\" had {} reads in {}s",
                table,
                pk,
                count,
                self.window.as_secs()
            ))
        } else {
            None
        }
    }

    /// Get current write count for a partition key.
    pub fn get_write_count(&self, table: &str, pk: &str) -> u32 {
        let key = format!("{}:{}", table, pk);
        let mut entries = self.entries.lock().unwrap();

        if let Some(entry) = entries.get_mut(&key) {
            entry.cleanup(self.window);
            entry.writes.len() as u32
        } else {
            0
        }
    }

    /// Get current read count for a partition key.
    pub fn get_read_count(&self, table: &str, pk: &str) -> u32 {
        let key = format!("{}:{}", table, pk);
        let mut entries = self.entries.lock().unwrap();

        if let Some(entry) = entries.get_mut(&key) {
            entry.cleanup(self.window);
            entry.reads.len() as u32
        } else {
            0
        }
    }

    /// Clear all tracked entries.
    pub fn clear(&self) {
        let mut entries = self.entries.lock().unwrap();
        entries.clear();
    }
}

impl HotPartitionTracker {
    /// Periodically cleanup old entries to prevent memory growth.
    fn maybe_cleanup(&self) {
        let mut last = self.last_cleanup.lock().unwrap();
        let now = Instant::now();

        // Cleanup every window duration
        if now.duration_since(*last) > self.window {
            *last = now;
            drop(last); // Release lock before acquiring entries lock

            let mut entries = self.entries.lock().unwrap();
            entries.retain(|_, entry| {
                entry.cleanup(self.window);
                !entry.is_empty()
            });
        }
    }
}

/// Register hot partition module with Python.
pub fn register_hot_partition(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<HotPartitionTracker>()?;
    Ok(())
}
