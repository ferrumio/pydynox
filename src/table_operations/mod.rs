//! Table management operations for DynamoDB.
//!
//! This module provides table lifecycle operations:
//! - `create` - Create a new table with optional GSIs and LSIs
//! - `delete` - Delete a table
//! - `exists` - Check if a table exists
//! - `wait` - Wait for table to become active
//! - `gsi` - GSI definition and parsing
//! - `lsi` - LSI definition and parsing

mod create;
mod delete;
mod exists;
mod gsi;
mod lsi;
mod wait;

// Re-export public functions
pub use create::create_table;
pub use delete::delete_table;
pub use exists::table_exists;
pub use gsi::parse_gsi_definitions;
pub use lsi::parse_lsi_definitions;
pub use wait::wait_for_table_active;
