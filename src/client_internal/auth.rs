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
use aws_config::sts::AssumeRoleProvider;
use aws_config::BehaviorVersion;
use aws_sdk_dynamodb::config::Credentials;

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
/// 2. AssumeRole (if role_arn is set)
/// 3. AWS profile (supports SSO profiles)
/// 4. Default chain (env vars, instance profile, container, EKS IRSA, GitHub OIDC, etc.)
pub async fn build_credential_provider(config: &AwsConfig) -> CredentialProvider {
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
        let base_config = aws_config::defaults(BehaviorVersion::latest()).load().await;
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
        let provider = ProfileFileCredentialsProvider::builder()
            .profile_name(profile_name)
            .build();
        return CredentialProvider::Profile(provider);
    }

    // 4. Default chain
    // Handles: env vars, ~/.aws/credentials, instance profile,
    // container credentials, EKS IRSA, GitHub OIDC, SSO
    CredentialProvider::Default
}
