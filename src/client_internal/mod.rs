//! Shared AWS client configuration and builders.
//!
//! This module contains the internal logic for building AWS clients:
//! - `auth`: Credential providers (static, profile, AssumeRole)
//! - `builder`: Client construction for DynamoDB, S3, KMS
//! - `config`: Shared AwsConfig struct
//!
//! All clients share the same configuration to avoid duplication.

mod auth;
mod builder;
mod config;

pub use builder::{build_client, build_kms_client, build_s3_client};
pub use config::AwsConfig;
