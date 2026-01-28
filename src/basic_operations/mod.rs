//! Basic DynamoDB operations module.
//!
//! This module provides the core CRUD operations for DynamoDB:
//! - `get` - Get a single item by key
//! - `put` - Put/create an item
//! - `delete` - Delete an item by key
//! - `update` - Update an item
//! - `query` - Query items by key condition
//! - `scan` - Scan all items in a table
//! - `partiql` - PartiQL statement execution
//!
//! All operations are async by default. Sync versions have `sync_` prefix.

mod delete;
mod get;
mod partiql;
mod put;
mod query;
mod scan;
mod update_op;

// Re-export async operations (default, no prefix)
pub use delete::delete_item;
pub use get::get_item;
pub use partiql::execute_statement;
pub use put::put_item;
pub use query::query;
pub use scan::{count, parallel_scan, scan};
pub use update_op::update_item;

// Re-export sync operations (with sync_ prefix)
pub use delete::sync_delete_item;
pub use get::sync_get_item;
pub use partiql::sync_execute_statement;
pub use put::sync_put_item;
pub use query::sync_query;
pub use scan::{sync_count, sync_parallel_scan, sync_scan};
pub use update_op::sync_update_item;
