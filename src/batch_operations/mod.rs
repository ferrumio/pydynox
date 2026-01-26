//! Batch operations module for DynamoDB.
//!
//! This module provides batch operations:
//! - `batch_write` - Write multiple items in a single request (async, default)
//! - `batch_get` - Get multiple items in a single request (async, default)
//! - `sync_batch_write` - Sync version of batch_write
//! - `sync_batch_get` - Sync version of batch_get
//!
//! Both handle automatic splitting to respect DynamoDB limits and
//! retry unprocessed items with exponential backoff.

mod get;
mod write;

// Re-export async operations (default, no prefix)
pub use get::batch_get;
pub use write::batch_write;

// Re-export sync operations (with sync_ prefix)
pub use get::sync_batch_get;
pub use write::sync_batch_write;
