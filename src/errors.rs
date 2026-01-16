//! Error types for pydynox.
//!
//! This module maps AWS SDK errors to Python exceptions.
//! Uses a single mapping function to avoid code duplication.

use aws_sdk_dynamodb::error::SdkError;
use pyo3::create_exception;
use pyo3::exceptions::PyException;
use pyo3::prelude::*;

// Create Python exception classes
create_exception!(pydynox, PydynoxException, PyException);
create_exception!(pydynox, ResourceNotFoundException, PydynoxException);
create_exception!(pydynox, ResourceInUseException, PydynoxException);
create_exception!(pydynox, ValidationException, PydynoxException);
create_exception!(pydynox, ConditionalCheckFailedException, PydynoxException);
create_exception!(pydynox, TransactionCanceledException, PydynoxException);
create_exception!(
    pydynox,
    ProvisionedThroughputExceededException,
    PydynoxException
);
create_exception!(pydynox, AccessDeniedException, PydynoxException);
create_exception!(pydynox, CredentialsException, PydynoxException);
create_exception!(pydynox, SerializationException, PydynoxException);
create_exception!(pydynox, ConnectionException, PydynoxException);
create_exception!(pydynox, EncryptionException, PydynoxException);
create_exception!(pydynox, S3AttributeException, PydynoxException);

/// Register exception classes with the Python module.
pub fn register_exceptions(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("PydynoxException", m.py().get_type::<PydynoxException>())?;
    m.add(
        "ResourceNotFoundException",
        m.py().get_type::<ResourceNotFoundException>(),
    )?;
    m.add(
        "ResourceInUseException",
        m.py().get_type::<ResourceInUseException>(),
    )?;
    m.add(
        "ValidationException",
        m.py().get_type::<ValidationException>(),
    )?;
    m.add(
        "ConditionalCheckFailedException",
        m.py().get_type::<ConditionalCheckFailedException>(),
    )?;
    m.add(
        "TransactionCanceledException",
        m.py().get_type::<TransactionCanceledException>(),
    )?;
    m.add(
        "ProvisionedThroughputExceededException",
        m.py().get_type::<ProvisionedThroughputExceededException>(),
    )?;
    m.add(
        "AccessDeniedException",
        m.py().get_type::<AccessDeniedException>(),
    )?;
    m.add(
        "CredentialsException",
        m.py().get_type::<CredentialsException>(),
    )?;
    m.add(
        "SerializationException",
        m.py().get_type::<SerializationException>(),
    )?;
    m.add(
        "ConnectionException",
        m.py().get_type::<ConnectionException>(),
    )?;
    m.add(
        "EncryptionException",
        m.py().get_type::<EncryptionException>(),
    )?;
    m.add(
        "S3AttributeException",
        m.py().get_type::<S3AttributeException>(),
    )?;
    Ok(())
}

/// Map any AWS SDK error to the appropriate Python exception.
///
/// This is the single entry point for error handling. All operations
/// should use this function to convert SDK errors to Python exceptions.
pub fn map_sdk_error<E, R>(err: SdkError<E, R>, table: Option<&str>) -> PyErr
where
    E: std::fmt::Debug + std::fmt::Display,
    R: std::fmt::Debug,
{
    // Get both display and debug representations
    let err_display = err.to_string();
    let err_debug = format!("{:?}", err);

    // Check for connection/dispatch errors first
    if err_debug.contains("dispatch failure")
        || err_debug.contains("DispatchFailure")
        || err_debug.contains("connection refused")
        || err_debug.contains("Connection refused")
        || err_debug.contains("ConnectError")
    {
        return ConnectionException::new_err(
            "Connection failed. Check if DynamoDB endpoint is reachable. \
            For local testing, make sure DynamoDB Local/LocalStack/Moto or any other emulator is running.",
        );
    }

    if err_debug.contains("timeout") || err_debug.contains("Timeout") {
        return ConnectionException::new_err(
            "Connection timed out. Check your network or endpoint.",
        );
    }

    // Check for credential errors first (these are dispatch failures, not service errors)
    if err_debug.contains("NoCredentialsError")
        || err_debug.contains("no credentials")
        || err_debug.contains("No credentials")
        || err_debug.contains("CredentialsError")
        || err_debug.contains("failed to load credentials")
    {
        return CredentialsException::new_err(
            "No AWS credentials found. Configure credentials via environment variables \
            (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY), AWS profile, or IAM role.",
        );
    }

    if err_debug.contains("InvalidAccessKeyId") || err_debug.contains("invalid access key") {
        return CredentialsException::new_err("Invalid AWS access key ID. Check your credentials.");
    }

    if err_debug.contains("SignatureDoesNotMatch") {
        return CredentialsException::new_err(
            "AWS signature mismatch. Check your secret access key.",
        );
    }

    if err_debug.contains("ExpiredToken") || err_debug.contains("expired") {
        return CredentialsException::new_err(
            "AWS credentials have expired. Refresh your session token.",
        );
    }

    // Extract error code from the debug string
    let error_code = extract_error_code(&err_debug);

    // Map based on error code
    match error_code.as_deref() {
        Some("ResourceNotFoundException") => {
            let msg = if let Some(t) = table {
                format!("Table '{}' not found", t)
            } else {
                "Resource not found".to_string()
            };
            ResourceNotFoundException::new_err(msg)
        }
        Some("ResourceInUseException") => {
            let msg = if let Some(t) = table {
                format!("Table '{}' already exists", t)
            } else {
                "Resource already in use".to_string()
            };
            ResourceInUseException::new_err(msg)
        }
        Some("ValidationException") => {
            // Try to extract the actual validation message
            let msg = extract_message(&err_debug).unwrap_or(err_display);
            ValidationException::new_err(msg)
        }
        Some("ConditionalCheckFailedException") => {
            ConditionalCheckFailedException::new_err("The condition expression evaluated to false")
        }
        Some("TransactionCanceledException") => {
            let reasons = extract_cancellation_reasons(&err_debug);
            let msg = if reasons.is_empty() {
                "Transaction was canceled".to_string()
            } else {
                format!("Transaction was canceled: {}", reasons.join("; "))
            };
            TransactionCanceledException::new_err(msg)
        }
        Some("ProvisionedThroughputExceededException") => {
            ProvisionedThroughputExceededException::new_err(
                "Request rate too high. Try again with exponential backoff.",
            )
        }
        Some("AccessDeniedException") => {
            let msg = extract_message(&err_debug)
                .unwrap_or_else(|| "Access denied. Check your IAM permissions.".to_string());
            AccessDeniedException::new_err(msg)
        }
        Some("UnrecognizedClientException") => CredentialsException::new_err(
            "Invalid AWS credentials. Check your access key and secret.",
        ),
        Some("ItemCollectionSizeLimitExceededException") => {
            ValidationException::new_err("Item collection size limit exceeded")
        }
        Some("RequestLimitExceeded") => ProvisionedThroughputExceededException::new_err(
            "Request limit exceeded. Try again later.",
        ),
        _ => {
            // For unknown errors, include as much detail as possible
            let msg = extract_message(&err_debug).unwrap_or_else(|| {
                // If we can't extract a message, use the debug string but clean it up
                if err_display == "service error" {
                    // The display is useless, use debug but truncate if too long
                    let clean = err_debug.replace('\n', " ").replace("  ", " ");
                    if clean.len() > 500 {
                        format!("{}...", &clean[..500])
                    } else {
                        clean
                    }
                } else {
                    err_display
                }
            });
            PydynoxException::new_err(msg)
        }
    }
}

/// Extract error code from AWS SDK error debug string.
fn extract_error_code(err_str: &str) -> Option<String> {
    // Look for patterns like: code: Some("ResourceNotFoundException")
    if let Some(start) = err_str.find("code: Some(\"") {
        let rest = &err_str[start + 12..];
        if let Some(end) = rest.find('"') {
            return Some(rest[..end].to_string());
        }
    }

    // Also check for error type names in the string
    let known_errors = [
        "ResourceNotFoundException",
        "ResourceInUseException",
        "ValidationException",
        "ConditionalCheckFailedException",
        "TransactionCanceledException",
        "ProvisionedThroughputExceededException",
        "ProvisionedThroughputExceededException",
        "AccessDeniedException",
        "UnrecognizedClientException",
        "ItemCollectionSizeLimitExceededException",
        "RequestLimitExceeded",
    ];

    for error in known_errors {
        if err_str.contains(error) {
            return Some(error.to_string());
        }
    }

    None
}

/// Extract the error message from AWS SDK error debug string.
fn extract_message(err_str: &str) -> Option<String> {
    // Look for patterns like: message: Some("The actual error message")
    if let Some(start) = err_str.find("message: Some(\"") {
        let rest = &err_str[start + 15..];
        if let Some(end) = rest.find('"') {
            return Some(rest[..end].to_string());
        }
    }
    None
}

/// Extract cancellation reasons from transaction error.
fn extract_cancellation_reasons(err_str: &str) -> Vec<String> {
    let mut reasons = Vec::new();

    if err_str.contains("ConditionalCheckFailed") {
        reasons.push("Condition check failed".to_string());
    }
    if err_str.contains("ItemCollectionSizeLimitExceeded") {
        reasons.push("Item collection size limit exceeded".to_string());
    }
    if err_str.contains("TransactionConflict") {
        reasons.push("Transaction conflict".to_string());
    }
    if err_str.contains("ProvisionedThroughputExceeded") {
        reasons.push("Throughput exceeded".to_string());
    }

    reasons
}

/// Map KMS SDK errors to Python exceptions.
///
/// Similar to map_sdk_error but for KMS-specific errors.
pub fn map_kms_error<E, R>(err: SdkError<E, R>) -> PyErr
where
    E: std::fmt::Debug + std::fmt::Display,
    R: std::fmt::Debug,
{
    let err_display = err.to_string();
    let err_debug = format!("{:?}", err);

    // Connection errors
    if err_debug.contains("dispatch failure")
        || err_debug.contains("DispatchFailure")
        || err_debug.contains("connection refused")
        || err_debug.contains("ConnectError")
    {
        return ConnectionException::new_err(
            "Connection to KMS failed. Check if the endpoint is reachable.",
        );
    }

    // Credential errors
    if err_debug.contains("NoCredentialsError")
        || err_debug.contains("no credentials")
        || err_debug.contains("CredentialsError")
    {
        return CredentialsException::new_err(
            "No AWS credentials found for KMS. Configure credentials via environment variables.",
        );
    }

    if err_debug.contains("InvalidAccessKeyId") {
        return CredentialsException::new_err("Invalid AWS access key ID for KMS.");
    }

    // KMS-specific errors
    if err_debug.contains("NotFoundException") || err_debug.contains("not found") {
        return EncryptionException::new_err("KMS key not found. Check the key ID or alias.");
    }

    if err_debug.contains("DisabledException") {
        return EncryptionException::new_err("KMS key is disabled.");
    }

    if err_debug.contains("InvalidKeyUsageException") {
        return EncryptionException::new_err("KMS key cannot be used for this operation.");
    }

    if err_debug.contains("KeyUnavailableException") {
        return EncryptionException::new_err("KMS key is not available. Try again later.");
    }

    if err_debug.contains("InvalidCiphertextException") {
        return EncryptionException::new_err("Invalid ciphertext. Data may be corrupted.");
    }

    if err_debug.contains("IncorrectKeyException") {
        return EncryptionException::new_err("Wrong KMS key used for decryption.");
    }

    if err_debug.contains("InvalidGrantTokenException") {
        return EncryptionException::new_err("Invalid grant token.");
    }

    if err_debug.contains("AccessDeniedException") {
        return AccessDeniedException::new_err(
            "Access denied to KMS key. Check your IAM permissions.",
        );
    }

    if err_debug.contains("ProvisionedThroughputExceededException")
        || err_debug.contains("LimitExceededException")
    {
        return ProvisionedThroughputExceededException::new_err(
            "KMS request rate too high. Try again later.",
        );
    }

    // Generic encryption error
    let msg = extract_message(&err_debug).unwrap_or(err_display);
    EncryptionException::new_err(format!("KMS operation failed: {}", msg))
}
