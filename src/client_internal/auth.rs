//! Authentication and credential providers.
//!
//! Supports multiple credential sources:
//! - Static credentials (access_key + secret_key)
//! - AssumeRole (cross-account)
//! - AWS Profile (including SSO profiles)
//! - Default chain (env vars, instance profile, container, EKS IRSA, GitHub OIDC, etc.)
//!
//! ## SSO Support
//!
//! SSO is supported via AWS profiles. Configure SSO with `aws configure sso`,
//! then pass the profile name to the client:
//!
//! ```python
//! client = DynamoDBClient(profile="my-sso-profile")
//! ```
//!
//! ## EKS IRSA / GitHub Actions OIDC
//!
//! These are automatically resolved by the default credential chain when
//! the env vars are set (injected automatically by EKS/GitHub).
//! Just use `DynamoDBClient()` without any parameters.

use aws_config::profile::ProfileFileCredentialsProvider;
use aws_config::provider_config::ProviderConfig;
use aws_config::sts::AssumeRoleProvider;
use aws_config::{BehaviorVersion, Region, SdkConfig};
use aws_sdk_dynamodb::config::Credentials;
use aws_smithy_runtime_api::client::http::SharedHttpClient;

use super::config::AwsConfig;

/// Credential provider type for the client.
pub enum CredentialProvider {
    /// Static credentials (access key + secret key)
    Static(Credentials),
    /// AWS profile from ~/.aws/credentials or ~/.aws/config (supports SSO)
    Profile(ProfileFileCredentialsProvider),
    /// AssumeRole for cross-account access
    AssumeRole(Box<AssumeRoleProvider>),
    /// Default credential chain (env, instance profile, container, EKS IRSA, GitHub OIDC, SSO)
    Default,
}

/// Build the credential provider based on configuration.
///
/// Priority order:
/// 1. Hardcoded credentials (access_key + secret_key)
/// 2. AssumeRole (if role_arn is set). If a profile is also set, its
///    credentials are used to call STS.
/// 3. AWS profile (supports SSO profiles)
/// 4. Default chain (env vars, instance profile, container, EKS IRSA, GitHub OIDC, etc.)
pub async fn build_credential_provider(
    config: &AwsConfig,
    http_client: Option<SharedHttpClient>,
    region: Option<Region>,
) -> CredentialProvider {
    // 1. Static credentials
    if let (Some(ak), Some(sk)) = (&config.access_key, &config.secret_key) {
        let creds = Credentials::new(
            ak.clone(),
            sk.clone(),
            config.session_token.clone(),
            None,
            "pydynox-hardcoded",
        );
        return CredentialProvider::Static(creds);
    }

    // 2. AssumeRole (cross-account)
    if let Some(role) = &config.role_arn {
        let base_config =
            assume_role_source_config(config.profile.as_deref(), http_client, region).await;
        let session_name = config
            .role_session_name
            .as_deref()
            .unwrap_or("pydynox-session");

        let mut builder = AssumeRoleProvider::builder(role.clone())
            .session_name(session_name)
            .configure(&base_config);

        if let Some(ext_id) = &config.external_id {
            builder = builder.external_id(ext_id.clone());
        }

        return CredentialProvider::AssumeRole(Box::new(builder.build().await));
    }

    // 3. Profile-based credentials (supports SSO profiles)
    if let Some(profile_name) = &config.profile {
        let provider = profile_credentials_provider(profile_name, http_client, region);
        return CredentialProvider::Profile(provider);
    }

    // 4. Default chain
    // Handles: env vars, ~/.aws/credentials, instance profile,
    // container credentials, EKS IRSA, GitHub OIDC, SSO
    CredentialProvider::Default
}

/// Config used to call STS for AssumeRole. A named profile, when given, is the
/// source identity instead of the default chain.
pub(crate) async fn assume_role_source_config(
    profile: Option<&str>,
    http_client: Option<SharedHttpClient>,
    region: Option<Region>,
) -> SdkConfig {
    let mut loader = aws_config::defaults(BehaviorVersion::latest());
    if let Some(ref http_client) = http_client {
        loader = loader
            .http_client(http_client.clone())
            .region(region.clone());
    }
    if let Some(profile_name) = profile {
        loader = loader.credentials_provider(profile_credentials_provider(
            profile_name,
            http_client,
            region,
        ));
    }
    loader.load().await
}

/// Keep profile STS and SSO requests on the client's HTTP transport.
fn profile_credentials_provider(
    profile_name: &str,
    http_client: Option<SharedHttpClient>,
    region: Option<Region>,
) -> ProfileFileCredentialsProvider {
    let mut builder = ProfileFileCredentialsProvider::builder().profile_name(profile_name);
    if let Some(http_client) = http_client {
        builder = builder.configure(
            &ProviderConfig::default()
                .with_http_client(http_client)
                .with_region(region),
        );
    }
    builder.build()
}
