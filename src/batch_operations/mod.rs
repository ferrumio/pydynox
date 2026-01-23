//! Batch operations module for DynamoDB.
//!
//! This module provides batch operations:
//! - `batch_write` - Write multiple items in a single request
//! - `batch_get` - Get multiple items in a single request
//!
//! Both handle automatic splitting to respect DynamoDB limits and
//! retry unprocessed items with exponential backoff.

mod get;
mod write;

// Re-export sync operations
pub use get::batch_get;
pub use write::batch_write;

// Re-export async operations
pub use get::async_batch_get;
pub use write::async_batch_write;
