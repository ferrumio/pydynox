//! Rate limiting module for DynamoDB operations.
//!
//! Provides token bucket-based rate limiting to prevent throttling.
//! Two strategies are available:
//! - [`FixedRate`]: Use when you know exactly how much capacity to use
//! - [`AdaptiveRate`]: Auto-adjusts based on throttling feedback

use pyo3::prelude::*;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Mutex;
use std::time::{Duration, Instant};

/// Token bucket for rate limiting with microsecond precision.
///
/// Uses the token bucket algorithm to control request rate.
/// Tokens are added at a fixed rate and consumed by operations.
pub struct TokenBucket {
    /// Current tokens (stored as microtokens for precision)
    tokens: AtomicU64,
    /// Maximum tokens allowed (burst capacity)
    max_tokens: f64,
    /// Tokens added per second
    refill_rate: AtomicU64,
    /// Last time tokens were refilled
    last_refill: Mutex<Instant>,
}

impl TokenBucket {
    /// Create a new token bucket.
    ///
    /// # Arguments
    ///
    /// * `rate` - Tokens per second
    /// * `burst` - Maximum tokens (burst capacity). Defaults to rate if None.
    pub fn new(rate: f64, burst: Option<f64>) -> Self {
        let max_tokens = burst.unwrap_or(rate);
        let initial_tokens = (max_tokens * 1_000_000.0) as u64;

        Self {
            tokens: AtomicU64::new(initial_tokens),
            max_tokens,
            refill_rate: AtomicU64::new((rate * 1_000_000.0) as u64),
            last_refill: Mutex::new(Instant::now()),
        }
    }

    /// Refill tokens based on elapsed time.
    fn refill(&self) {
        let mut last = self.last_refill.lock().unwrap();
        let now = Instant::now();
        let elapsed = now.duration_since(*last).as_secs_f64();

        if elapsed > 0.0 {
            let rate = self.refill_rate.load(Ordering::Relaxed) as f64 / 1_000_000.0;
            let new_tokens = elapsed * rate;
            let max_microtokens = (self.max_tokens * 1_000_000.0) as u64;

            let current = self.tokens.load(Ordering::Relaxed);
            let added = (new_tokens * 1_000_000.0) as u64;
            let new_total = (current + added).min(max_microtokens);

            self.tokens.store(new_total, Ordering::Relaxed);
            *last = now;
        }
    }

    /// Try to acquire tokens without blocking.
    ///
    /// Returns true if tokens were acquired, false otherwise.
    pub fn try_acquire(&self, tokens: f64) -> bool {
        self.refill();

        let microtokens = (tokens * 1_000_000.0) as u64;
        let current = self.tokens.load(Ordering::Relaxed);

        if current >= microtokens {
            self.tokens.fetch_sub(microtokens, Ordering::Relaxed);
            true
        } else {
            false
        }
    }

    /// Wait until tokens are available, then consume them.
    ///
    /// This is a blocking operation that sleeps until enough tokens
    /// are available.
    pub fn acquire(&self, tokens: f64) {
        loop {
            self.refill();

            let microtokens = (tokens * 1_000_000.0) as u64;
            let current = self.tokens.load(Ordering::Relaxed);

            if current >= microtokens {
                self.tokens.fetch_sub(microtokens, Ordering::Relaxed);
                return;
            }

            // Calculate wait time
            let needed = microtokens - current;
            let rate = self.refill_rate.load(Ordering::Relaxed) as f64;
            let wait_secs = needed as f64 / rate;

            // Sleep for the calculated time (minimum 1ms)
            let sleep_duration = Duration::from_secs_f64(wait_secs.max(0.001));
            std::thread::sleep(sleep_duration);
        }
    }

    /// Update the refill rate.
    pub fn set_rate(&self, rate: f64) {
        self.refill_rate
            .store((rate * 1_000_000.0) as u64, Ordering::Relaxed);
    }

    /// Get the current rate.
    pub fn get_rate(&self) -> f64 {
        self.refill_rate.load(Ordering::Relaxed) as f64 / 1_000_000.0
    }
}

/// Metrics for monitoring rate limiter behavior.
#[pyclass]
#[derive(Default)]
pub struct RateLimitMetrics {
    /// Total RCU consumed
    consumed_rcu: AtomicU64,
    /// Total WCU consumed
    consumed_wcu: AtomicU64,
    /// Number of times throttled
    throttle_count: AtomicU64,
}

impl RateLimitMetrics {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn add_rcu(&self, rcu: f64) {
        let micros = (rcu * 1_000_000.0) as u64;
        self.consumed_rcu.fetch_add(micros, Ordering::Relaxed);
    }

    pub fn add_wcu(&self, wcu: f64) {
        let micros = (wcu * 1_000_000.0) as u64;
        self.consumed_wcu.fetch_add(micros, Ordering::Relaxed);
    }

    pub fn record_throttle(&self) {
        self.throttle_count.fetch_add(1, Ordering::Relaxed);
    }
}

#[pymethods]
impl RateLimitMetrics {
    /// Get total consumed RCU.
    #[getter]
    fn get_consumed_rcu(&self) -> f64 {
        self.consumed_rcu.load(Ordering::Relaxed) as f64 / 1_000_000.0
    }

    /// Get total consumed WCU.
    #[getter]
    fn get_consumed_wcu(&self) -> f64 {
        self.consumed_wcu.load(Ordering::Relaxed) as f64 / 1_000_000.0
    }

    /// Get throttle count.
    #[getter]
    fn get_throttle_count(&self) -> u64 {
        self.throttle_count.load(Ordering::Relaxed)
    }

    /// Reset all metrics to zero.
    fn reset(&self) {
        self.consumed_rcu.store(0, Ordering::Relaxed);
        self.consumed_wcu.store(0, Ordering::Relaxed);
        self.throttle_count.store(0, Ordering::Relaxed);
    }
}

/// Fixed rate limiter.
///
/// Use when you know exactly how much capacity to use.
/// The rate stays constant unless you change it manually.
#[pyclass]
pub struct FixedRate {
    rcu_bucket: Option<TokenBucket>,
    wcu_bucket: Option<TokenBucket>,
    metrics: RateLimitMetrics,
}

#[pymethods]
impl FixedRate {
    /// Create a new fixed rate limiter.
    ///
    /// # Arguments
    ///
    /// * `rcu` - Read capacity units per second (optional)
    /// * `wcu` - Write capacity units per second (optional)
    /// * `burst` - Burst capacity (defaults to rate value)
    #[new]
    #[pyo3(signature = (rcu=None, wcu=None, burst=None))]
    pub fn new(rcu: Option<f64>, wcu: Option<f64>, burst: Option<f64>) -> Self {
        let rcu_bucket = rcu.map(|r| TokenBucket::new(r, burst));
        let wcu_bucket = wcu.map(|w| TokenBucket::new(w, burst));

        Self {
            rcu_bucket,
            wcu_bucket,
            metrics: RateLimitMetrics::new(),
        }
    }

    /// Get the configured RCU rate.
    #[getter]
    fn rcu(&self) -> Option<f64> {
        self.rcu_bucket.as_ref().map(|b| b.get_rate())
    }

    /// Get the configured WCU rate.
    #[getter]
    fn wcu(&self) -> Option<f64> {
        self.wcu_bucket.as_ref().map(|b| b.get_rate())
    }

    /// Get metrics.
    #[getter]
    fn metrics(&self) -> RateLimitMetrics {
        RateLimitMetrics {
            consumed_rcu: AtomicU64::new(self.metrics.consumed_rcu.load(Ordering::Relaxed)),
            consumed_wcu: AtomicU64::new(self.metrics.consumed_wcu.load(Ordering::Relaxed)),
            throttle_count: AtomicU64::new(self.metrics.throttle_count.load(Ordering::Relaxed)),
        }
    }

    /// Get total consumed RCU.
    #[getter]
    fn consumed_rcu(&self) -> f64 {
        self.metrics.consumed_rcu.load(Ordering::Relaxed) as f64 / 1_000_000.0
    }

    /// Get total consumed WCU.
    #[getter]
    fn consumed_wcu(&self) -> f64 {
        self.metrics.consumed_wcu.load(Ordering::Relaxed) as f64 / 1_000_000.0
    }

    /// Get throttle count.
    #[getter]
    fn throttle_count(&self) -> u64 {
        self.metrics.throttle_count.load(Ordering::Relaxed)
    }

    /// Acquire read capacity (called from Python).
    fn _acquire_rcu(&self, rcu: f64) {
        self.acquire_rcu(rcu);
    }

    /// Acquire write capacity (called from Python).
    fn _acquire_wcu(&self, wcu: f64) {
        self.acquire_wcu(wcu);
    }

    /// Record a throttle event (called from Python).
    fn _on_throttle(&self) {
        self.on_throttle();
    }
}

impl FixedRate {
    /// Acquire read capacity.
    pub fn acquire_rcu(&self, rcu: f64) {
        if let Some(bucket) = &self.rcu_bucket {
            bucket.acquire(rcu);
        }
        self.metrics.add_rcu(rcu);
    }

    /// Acquire write capacity.
    pub fn acquire_wcu(&self, wcu: f64) {
        if let Some(bucket) = &self.wcu_bucket {
            bucket.acquire(wcu);
        }
        self.metrics.add_wcu(wcu);
    }

    /// Record a throttle event.
    pub fn on_throttle(&self) {
        self.metrics.record_throttle();
    }
}

/// Adaptive rate limiter that adjusts based on throttling.
///
/// Starts at 50% of max rate. When throttled, reduces by 20%.
/// When no throttle for 10 seconds, increases by 10%.
#[pyclass]
pub struct AdaptiveRate {
    rcu_bucket: TokenBucket,
    wcu_bucket: Option<TokenBucket>,
    max_rcu: f64,
    min_rcu: f64,
    max_wcu: Option<f64>,
    min_wcu: f64,
    current_rcu: AtomicU64,
    current_wcu: AtomicU64,
    last_throttle: Mutex<Option<Instant>>,
    last_increase_check: Mutex<Instant>,
    metrics: RateLimitMetrics,
}

#[pymethods]
impl AdaptiveRate {
    /// Create a new adaptive rate limiter.
    ///
    /// # Arguments
    ///
    /// * `max_rcu` - Maximum read capacity units per second
    /// * `max_wcu` - Maximum write capacity units per second (optional)
    /// * `min_rcu` - Minimum RCU (default: 1)
    /// * `min_wcu` - Minimum WCU (default: 1)
    #[new]
    #[pyo3(signature = (max_rcu, max_wcu=None, min_rcu=None, min_wcu=None))]
    pub fn new(
        max_rcu: f64,
        max_wcu: Option<f64>,
        min_rcu: Option<f64>,
        min_wcu: Option<f64>,
    ) -> Self {
        let min_rcu = min_rcu.unwrap_or(1.0);
        let min_wcu = min_wcu.unwrap_or(1.0);

        // Start at 50% of max
        let initial_rcu = max_rcu * 0.5;
        let initial_wcu = max_wcu.map(|m| m * 0.5);

        let rcu_bucket = TokenBucket::new(initial_rcu, Some(max_rcu));
        let wcu_bucket = initial_wcu.map(|w| TokenBucket::new(w, max_wcu));

        Self {
            rcu_bucket,
            wcu_bucket,
            max_rcu,
            min_rcu,
            max_wcu,
            min_wcu,
            current_rcu: AtomicU64::new((initial_rcu * 1_000_000.0) as u64),
            current_wcu: AtomicU64::new(initial_wcu.map(|w| (w * 1_000_000.0) as u64).unwrap_or(0)),
            last_throttle: Mutex::new(None),
            last_increase_check: Mutex::new(Instant::now()),
            metrics: RateLimitMetrics::new(),
        }
    }

    /// Get the current RCU rate.
    #[getter]
    fn current_rcu(&self) -> f64 {
        self.current_rcu.load(Ordering::Relaxed) as f64 / 1_000_000.0
    }

    /// Get the current WCU rate.
    #[getter]
    fn current_wcu(&self) -> Option<f64> {
        if self.wcu_bucket.is_some() {
            Some(self.current_wcu.load(Ordering::Relaxed) as f64 / 1_000_000.0)
        } else {
            None
        }
    }

    /// Get the max RCU.
    #[getter]
    fn max_rcu(&self) -> f64 {
        self.max_rcu
    }

    /// Get the max WCU.
    #[getter]
    fn max_wcu(&self) -> Option<f64> {
        self.max_wcu
    }

    /// Get total consumed RCU.
    #[getter]
    fn consumed_rcu(&self) -> f64 {
        self.metrics.consumed_rcu.load(Ordering::Relaxed) as f64 / 1_000_000.0
    }

    /// Get total consumed WCU.
    #[getter]
    fn consumed_wcu(&self) -> f64 {
        self.metrics.consumed_wcu.load(Ordering::Relaxed) as f64 / 1_000_000.0
    }

    /// Get throttle count.
    #[getter]
    fn throttle_count(&self) -> u64 {
        self.metrics.throttle_count.load(Ordering::Relaxed)
    }

    /// Acquire read capacity (called from Python).
    fn _acquire_rcu(&self, rcu: f64) {
        self.acquire_rcu(rcu);
    }

    /// Acquire write capacity (called from Python).
    fn _acquire_wcu(&self, wcu: f64) {
        self.acquire_wcu(wcu);
    }

    /// Record a throttle event (called from Python).
    fn _on_throttle(&self) {
        self.on_throttle();
    }
}

impl AdaptiveRate {
    /// Acquire read capacity.
    pub fn acquire_rcu(&self, rcu: f64) {
        self.maybe_increase();
        self.rcu_bucket.acquire(rcu);
        self.metrics.add_rcu(rcu);
    }

    /// Acquire write capacity.
    pub fn acquire_wcu(&self, wcu: f64) {
        self.maybe_increase();
        if let Some(bucket) = &self.wcu_bucket {
            bucket.acquire(wcu);
        }
        self.metrics.add_wcu(wcu);
    }

    /// Called when DynamoDB returns ProvisionedThroughputExceededException.
    ///
    /// Reduces rate by 20%, but not below minimum.
    pub fn on_throttle(&self) {
        self.metrics.record_throttle();

        // Reduce RCU by 20%
        let current = self.current_rcu.load(Ordering::Relaxed) as f64 / 1_000_000.0;
        let new_rate = (current * 0.8).max(self.min_rcu);
        self.current_rcu
            .store((new_rate * 1_000_000.0) as u64, Ordering::Relaxed);
        self.rcu_bucket.set_rate(new_rate);

        // Reduce WCU by 20% if configured
        if let Some(bucket) = &self.wcu_bucket {
            let current = self.current_wcu.load(Ordering::Relaxed) as f64 / 1_000_000.0;
            let new_rate = (current * 0.8).max(self.min_wcu);
            self.current_wcu
                .store((new_rate * 1_000_000.0) as u64, Ordering::Relaxed);
            bucket.set_rate(new_rate);
        }

        // Record throttle time
        let mut last = self.last_throttle.lock().unwrap();
        *last = Some(Instant::now());
    }

    /// Check if we should increase rate (no throttle for 10s).
    fn maybe_increase(&self) {
        let mut last_check = self.last_increase_check.lock().unwrap();
        let now = Instant::now();

        // Only check every second
        if now.duration_since(*last_check).as_secs() < 1 {
            return;
        }
        *last_check = now;

        // Check if no throttle for 10 seconds
        let last_throttle = self.last_throttle.lock().unwrap();
        let should_increase = match *last_throttle {
            None => true,
            Some(t) => now.duration_since(t).as_secs() >= 10,
        };

        if should_increase {
            // Increase RCU by 10%
            let current = self.current_rcu.load(Ordering::Relaxed) as f64 / 1_000_000.0;
            let new_rate = (current * 1.1).min(self.max_rcu);
            self.current_rcu
                .store((new_rate * 1_000_000.0) as u64, Ordering::Relaxed);
            self.rcu_bucket.set_rate(new_rate);

            // Increase WCU by 10% if configured
            if let (Some(bucket), Some(max)) = (&self.wcu_bucket, self.max_wcu) {
                let current = self.current_wcu.load(Ordering::Relaxed) as f64 / 1_000_000.0;
                let new_rate = (current * 1.1).min(max);
                self.current_wcu
                    .store((new_rate * 1_000_000.0) as u64, Ordering::Relaxed);
                bucket.set_rate(new_rate);
            }
        }
    }
}

/// Trait for rate limiters.
pub trait RateLimiter: Send + Sync {
    fn acquire_rcu(&self, rcu: f64);
    fn acquire_wcu(&self, wcu: f64);
    fn on_throttle(&self);
}

impl RateLimiter for FixedRate {
    fn acquire_rcu(&self, rcu: f64) {
        self.acquire_rcu(rcu);
    }

    fn acquire_wcu(&self, wcu: f64) {
        self.acquire_wcu(wcu);
    }

    fn on_throttle(&self) {
        self.on_throttle();
    }
}

impl RateLimiter for AdaptiveRate {
    fn acquire_rcu(&self, rcu: f64) {
        self.acquire_rcu(rcu);
    }

    fn acquire_wcu(&self, wcu: f64) {
        self.acquire_wcu(wcu);
    }

    fn on_throttle(&self) {
        self.on_throttle();
    }
}
