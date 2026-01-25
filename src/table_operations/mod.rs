//! Table management operations for DynamoDB.
//!
//! This module provides table lifecycle operations:
//! - `create` - Create a new table with optional GSIs and LSIs
//! - `delete` - Delete a table
//! - `exists` - Check if a table exists
//! - `wait` - Wait for table to become active
//! - `gsi` - GSI definition and parsing
//! - `lsi` - LSI definition and parsing
//!
//! ## Async-First API
//!
//! Table operations follow the async-first pattern:
//! - `create_table()` - async (returns Python awaitable)
//! - `sync_create_table()` - sync (blocks until complete)
//!
//! Same pattern for delete_table, table_exists, wait_for_table_active.

mod create;
mod delete;
mod exists;
mod gsi;
mod lsi;
mod wait;

// Re-export sync operations (with sync_ prefix)
pub use create::sync_create_table;
pub use delete::sync_delete_table;
pub use exists::sync_table_exists;
pub use wait::sync_wait_for_table_active;

// Re-export async operations (no prefix - default)
pub use create::create_table;
pub use delete::delete_table;
pub use exists::table_exists;
pub use wait::wait_for_table_active;

// Re-export GSI/LSI parsing (unchanged)
pub use gsi::parse_gsi_definitions;
pub use lsi::parse_lsi_definitions;
