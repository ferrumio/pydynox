//! Basic DynamoDB operations module.
//!
//! This module provides the core CRUD operations for DynamoDB:
//! - `get` - Get a single item by key
//! - `put` - Put/create an item
//! - `delete` - Delete an item by key
//! - `update` - Update an item
//! - `query` - Query items by key condition
//! - `partiql` - PartiQL statement execution

mod delete;
mod get;
mod partiql;
mod put;
mod query;
mod update_op;

// Re-export sync operations
pub use delete::delete_item;
pub use get::get_item;
pub use partiql::execute_statement;
pub use put::put_item;
pub use query::query;
pub use update_op::update_item;

// Re-export async operations
pub use delete::async_delete_item;
pub use get::async_get_item;
pub use partiql::async_execute_statement;
pub use put::async_put_item;
pub use query::async_query;
pub use update_op::async_update_item;
