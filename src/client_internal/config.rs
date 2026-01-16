//! Shared AWS configuration for all clients (DynamoDB, S3, KMS).
//!
//! This module provides a single configuration struct that all AWS clients use.
//! This avoids code duplication and ensures consistent behavior across services.

use std::sync::Arc;

/// Shared configuration for all AWS clients.
///
/// Created once by DynamoDBClient, then shared with S3 and KMS clients
/// when they are lazily initialized.
#[derive(Default, Clone)]
pub struct AwsConfig {
    // Region
    pub region: Option<String>,

    // Basic credentials
    pub access_key: Option<String>,
    pub secret_key: Option<String>,
    pub session_token: Option<String>,

    // Profile-based credentials (supports SSO)
    pub profile: Option<String>,

    // AssumeRole credentials
    pub role_arn: Option<String>,
    pub role_session_name: Option<String>,
    pub external_id: Option<String>,

    // Endpoint override (for local testing)
    pub endpoint_url: Option<String>,

    // Timeouts (in seconds)
    pub connect_timeout: Option<f64>,
    pub read_timeout: Option<f64>,

    // Retries
    pub max_retries: Option<u32>,

    // Proxy (sets HTTPS_PROXY env var, stored for reference)
    #[allow(dead_code)]
    pub proxy_url: Option<String>,
}

impl AwsConfig {
    /// Get the effective region (from config, env, or default).
    pub fn effective_region(&self) -> String {
        self.region.clone().unwrap_or_else(|| {
            std::env::var("AWS_REGION")
                .or_else(|_| std::env::var("AWS_DEFAULT_REGION"))
                .unwrap_or_else(|_| "us-east-1".to_string())
        })
    }

    /// Get the effective endpoint URL for DynamoDB.
    pub fn dynamodb_endpoint(&self) -> Option<String> {
        self.endpoint_url.clone().or_else(|| {
            std::env::var("AWS_ENDPOINT_URL_DYNAMODB")
                .or_else(|_| std::env::var("AWS_ENDPOINT_URL"))
                .ok()
        })
    }

    /// Get the effective endpoint URL for S3.
    pub fn s3_endpoint(&self) -> Option<String> {
        self.endpoint_url.clone().or_else(|| {
            std::env::var("AWS_ENDPOINT_URL_S3")
                .or_else(|_| std::env::var("AWS_ENDPOINT_URL"))
                .ok()
        })
    }

    /// Get the effective endpoint URL for KMS.
    pub fn kms_endpoint(&self) -> Option<String> {
        self.endpoint_url.clone().or_else(|| {
            std::env::var("AWS_ENDPOINT_URL_KMS")
                .or_else(|_| std::env::var("AWS_ENDPOINT_URL"))
                .ok()
        })
    }

    /// Create a shareable Arc wrapper.
    pub fn into_arc(self) -> Arc<AwsConfig> {
        Arc::new(self)
    }
}
