//! Client configuration options.

/// Configuration for creating a DynamoDB client.
#[derive(Default, Clone)]
pub struct ClientConfig {
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

impl ClientConfig {
    /// Get the effective region (from config, env, or default).
    pub fn effective_region(&self) -> String {
        self.region.clone().unwrap_or_else(|| {
            std::env::var("AWS_REGION")
                .or_else(|_| std::env::var("AWS_DEFAULT_REGION"))
                .unwrap_or_else(|_| "us-east-1".to_string())
        })
    }
}
