//! Client builders for all AWS services (DynamoDB, S3, KMS).
//!
//! Uses shared AwsConfig to avoid code duplication.

use std::time::Duration;

use aws_config::BehaviorVersion;
use aws_config::meta::region::RegionProviderChain;
use aws_config::retry::RetryConfig;
use aws_config::timeout::TimeoutConfig;
use aws_sdk_dynamodb::Client as DynamoDbClient;
use aws_sdk_kms::Client as KmsClient;
use aws_sdk_s3::Client as S3Client;

use super::auth::{CredentialProvider, build_credential_provider};
use super::config::AwsConfig;

/// Build the base AWS SDK config from AwsConfig.
///
/// This is shared by all client builders to avoid duplication.
async fn build_sdk_config(
    config: &AwsConfig,
    region_override: Option<String>,
) -> aws_config::SdkConfig {
    // Use override region if provided, otherwise use config region
    let effective_region = region_override.or_else(|| config.region.clone());

    let region_provider =
        RegionProviderChain::first_try(effective_region.map(aws_config::Region::new))
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
    let cred_provider = build_credential_provider(config).await;
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

    config_loader.load().await
}

/// Build DynamoDB client from shared config.
pub async fn build_dynamodb_client(config: &AwsConfig) -> Result<DynamoDbClient, String> {
    let sdk_config = build_sdk_config(config, None).await;
    let mut dynamo_config = aws_sdk_dynamodb::config::Builder::from(&sdk_config);

    if let Some(url) = config.dynamodb_endpoint() {
        dynamo_config = dynamo_config.endpoint_url(url);
    }

    Ok(DynamoDbClient::from_conf(dynamo_config.build()))
}

/// Build S3 client from shared config.
///
/// Optionally override region (S3 bucket may be in different region).
pub async fn build_s3_client(
    config: &AwsConfig,
    region_override: Option<String>,
) -> Result<S3Client, String> {
    let sdk_config = build_sdk_config(config, region_override).await;
    let mut s3_config = aws_sdk_s3::config::Builder::from(&sdk_config);

    if let Some(url) = config.s3_endpoint() {
        s3_config = s3_config.endpoint_url(url).force_path_style(true);
    }

    Ok(S3Client::from_conf(s3_config.build()))
}

/// Build KMS client from shared config.
///
/// Optionally override region (KMS key may be in different region).
pub async fn build_kms_client(
    config: &AwsConfig,
    region_override: Option<String>,
) -> Result<KmsClient, String> {
    let sdk_config = build_sdk_config(config, region_override).await;
    let mut kms_config = aws_sdk_kms::config::Builder::from(&sdk_config);

    if let Some(url) = config.kms_endpoint() {
        kms_config = kms_config.endpoint_url(url);
    }

    Ok(KmsClient::from_conf(kms_config.build()))
}

// Backward compatibility alias
pub async fn build_client(config: AwsConfig) -> Result<DynamoDbClient, String> {
    build_dynamodb_client(&config).await
}
