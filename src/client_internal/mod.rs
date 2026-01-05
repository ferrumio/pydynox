//! DynamoDB client internal modules.
//!
//! This module contains the internal logic for building the DynamoDB client:
//! - `auth`: Credential providers (static, profile, AssumeRole)
//! - `builder`: Client construction logic
//! - `config`: Configuration struct
//!
//! The PyO3 bindings remain in `src/client.rs`.

mod auth;
mod builder;
mod config;

pub use auth::{build_credential_provider, CredentialProvider};
pub use builder::build_client;
pub use config::ClientConfig;
