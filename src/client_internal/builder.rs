//! Client builder - constructs the AWS SDK DynamoDB client.

use std::time::Duration;

use aws_config::meta::region::RegionProviderChain;
use aws_config::retry::RetryConfig;
use aws_config::timeout::TimeoutConfig;
use aws_config::BehaviorVersion;
use aws_sdk_dynamodb::Client;

use super::auth::{build_credential_provider, CredentialProvider};
use super::config::ClientConfig;

/// Build the AWS SDK DynamoDB client from configuration.
pub async fn build_client(config: ClientConfig) -> Result<Client, String> {
    let region_provider = RegionProviderChain::first_try(
        config
            .region
            .clone()
            .map(aws_sdk_dynamodb::config::Region::new),
    )
    .or_default_provider()
    .or_else("us-east-1");

    let mut config_loader = aws_config::defaults(BehaviorVersion::latest()).region(region_provider);

    // Configure timeouts
    if config.connect_timeout.is_some() || config.read_timeout.is_some() {
        let mut timeout_builder = TimeoutConfig::builder();
        if let Some(ct) = config.connect_timeout {
            timeout_builder = timeout_builder.connect_timeout(Duration::from_secs_f64(ct));
        }
        if let Some(rt) = config.read_timeout {
            timeout_builder = timeout_builder.read_timeout(Duration::from_secs_f64(rt));
        }
        config_loader = config_loader.timeout_config(timeout_builder.build());
    }

    // Configure retries
    if let Some(retries) = config.max_retries {
        let retry_config = RetryConfig::standard().with_max_attempts(retries);
        config_loader = config_loader.retry_config(retry_config);
    }

    // Configure credentials
    let cred_provider = build_credential_provider(&config).await;
    match cred_provider {
        CredentialProvider::Static(creds) => {
            config_loader = config_loader.credentials_provider(creds);
        }
        CredentialProvider::Profile(provider) => {
            config_loader = config_loader.credentials_provider(provider);
        }
        CredentialProvider::AssumeRole(provider) => {
            config_loader = config_loader.credentials_provider(*provider);
        }
        CredentialProvider::Default => {
            // Use default chain, no explicit provider needed
        }
    }

    let sdk_config = config_loader.load().await;
    let mut dynamo_config = aws_sdk_dynamodb::config::Builder::from(&sdk_config);

    // Configure endpoint override (from config or AWS_ENDPOINT_URL env var)
    if let Some(url) = config.effective_endpoint_url() {
        dynamo_config = dynamo_config.endpoint_url(url);
    }

    Ok(Client::from_conf(dynamo_config.build()))
}
