//! Transaction operations module for DynamoDB.
//!
//! Handles transactional read and write operations with all-or-nothing semantics.
//! All operations in a transaction either succeed together or fail together.
//!
//! This module provides:
//! - `transact_write` / `sync_transact_write` - Write multiple items atomically
//! - `transact_get` / `sync_transact_get` - Read multiple items atomically

mod get;
mod write;

// Re-export sync operations (with sync_ prefix)
pub use get::sync_transact_get;
pub use write::sync_transact_write;

// Re-export async operations (default, no prefix)
pub use get::transact_get;
pub use write::transact_write;
