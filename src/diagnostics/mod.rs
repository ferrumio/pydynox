//! Diagnostics tools for DynamoDB access patterns.
//!
//! This module provides tools for monitoring and debugging DynamoDB usage:
//! - Hot partition detection

mod hot_partition;

pub use hot_partition::register_hot_partition;
