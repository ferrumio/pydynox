//! Error types for pydynox.
//!
//! This module maps AWS SDK errors to Python exceptions.
//! Uses unified error mapping for DynamoDB, S3, and KMS.

use aws_sdk_dynamodb::error::SdkError;
use aws_sdk_dynamodb::types::AttributeValue;
use pyo3::create_exception;
use pyo3::exceptions::PyException;
use pyo3::prelude::*;
use std::collections::HashMap;

use crate::conversions::attribute_values_to_py_dict;

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
create_exception!(pydynox, S3Exception, PydynoxException);

// Keep S3AttributeException as alias for backward compatibility
create_exception!(pydynox, S3AttributeException, S3Exception);

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
    m.add("S3Exception", m.py().get_type::<S3Exception>())?;
    // Backward compatibility
    m.add(
        "S3AttributeException",
        m.py().get_type::<S3AttributeException>(),
    )?;
    Ok(())
}

/// AWS service type for error context.
#[derive(Debug, Clone, Copy)]
pub enum AwsService {
    DynamoDB,
    S3,
    Kms,
}

impl AwsService {
    fn name(&self) -> &'static str {
        match self {
            AwsService::DynamoDB => "DynamoDB",
            AwsService::S3 => "S3",
            AwsService::Kms => "KMS",
        }
    }
}

// ========== UNIFIED ERROR MAPPING ==========

/// Map common AWS errors (connection, credentials, access).
///
/// Returns Some(PyErr) if it's a common error, None otherwise.
fn map_common_error(err_debug: &str, service: AwsService) -> Option<PyErr> {
    // Connection errors
    if err_debug.contains("dispatch failure")
        || err_debug.contains("DispatchFailure")
        || err_debug.contains("connection refused")
        || err_debug.contains("Connection refused")
        || err_debug.contains("ConnectError")
    {
        return Some(ConnectionException::new_err(format!(
            "Connection failed to {}. Check if the endpoint is reachable.",
            service.name()
        )));
    }

    if err_debug.contains("timeout") || err_debug.contains("Timeout") {
        return Some(ConnectionException::new_err(format!(
            "Connection timed out to {}. Check your network or endpoint.",
            service.name()
        )));
    }

    // Credential errors
    if err_debug.contains("NoCredentialsError")
        || err_debug.contains("no credentials")
        || err_debug.contains("No credentials")
        || err_debug.contains("CredentialsError")
        || err_debug.contains("failed to load credentials")
    {
        return Some(CredentialsException::new_err(
            "No AWS credentials found. Configure credentials via environment variables \
            (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY), AWS profile, or IAM role.",
        ));
    }

    if err_debug.contains("InvalidAccessKeyId") || err_debug.contains("invalid access key") {
        return Some(CredentialsException::new_err(
            "Invalid AWS access key ID. Check your credentials.",
        ));
    }

    if err_debug.contains("SignatureDoesNotMatch") {
        return Some(CredentialsException::new_err(
            "AWS signature mismatch. Check your secret access key.",
        ));
    }

    if err_debug.contains("ExpiredToken") || err_debug.contains("expired") {
        return Some(CredentialsException::new_err(
            "AWS credentials have expired. Refresh your session token.",
        ));
    }

    if err_debug.contains("UnrecognizedClientException") {
        return Some(CredentialsException::new_err(
            "Invalid AWS credentials. Check your access key and secret.",
        ));
    }

    // Access denied
    if err_debug.contains("AccessDeniedException") || err_debug.contains("Access Denied") {
        let msg = extract_message(err_debug).unwrap_or_else(|| {
            format!(
                "Access denied to {}. Check your IAM permissions.",
                service.name()
            )
        });
        return Some(AccessDeniedException::new_err(msg));
    }

    // Rate limiting
    if err_debug.contains("ProvisionedThroughputExceededException")
        || err_debug.contains("LimitExceededException")
        || err_debug.contains("RequestLimitExceeded")
        || err_debug.contains("SlowDown")
        || err_debug.contains("Throttling")
    {
        return Some(ProvisionedThroughputExceededException::new_err(format!(
            "{} request rate too high. Try again with exponential backoff.",
            service.name()
        )));
    }

    None
}

/// Map DynamoDB-specific errors.
pub fn map_sdk_error<E, R>(err: SdkError<E, R>, table: Option<&str>) -> PyErr
where
    E: std::fmt::Debug + std::fmt::Display,
    R: std::fmt::Debug,
{
    let err_display = err.to_string();
    let err_debug = format!("{:?}", err);

    // Check common errors first
    if let Some(py_err) = map_common_error(&err_debug, AwsService::DynamoDB) {
        return py_err;
    }

    // DynamoDB-specific errors
    let error_code = extract_error_code(&err_debug);

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
        Some("ItemCollectionSizeLimitExceededException") => {
            ValidationException::new_err("Item collection size limit exceeded")
        }
        _ => {
            let msg = extract_message(&err_debug).unwrap_or_else(|| {
                if err_display == "service error" {
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

/// Map DynamoDB errors with optional item data for ConditionalCheckFailedException.
///
/// When a conditional check fails and the item is available, this creates an exception
/// with the item attached so users can see what caused the failure.
pub fn map_sdk_error_with_item<E, R>(
    py: Python<'_>,
    err: SdkError<E, R>,
    table: Option<&str>,
    item: Option<HashMap<String, AttributeValue>>,
) -> PyErr
where
    E: std::fmt::Debug + std::fmt::Display,
    R: std::fmt::Debug,
{
    let err_debug = format!("{:?}", err);
    let error_code = extract_error_code(&err_debug);

    // Only handle ConditionalCheckFailedException with item specially
    if error_code.as_deref() == Some("ConditionalCheckFailedException") {
        if let Some(item_data) = item {
            // Convert item to Python dict
            if let Ok(py_item) = attribute_values_to_py_dict(py, item_data) {
                // Create exception with item attribute
                let exc = ConditionalCheckFailedException::new_err(
                    "The condition expression evaluated to false",
                );
                // Set the item attribute on the exception
                if let Ok(exc_val) = exc.value(py).getattr("__class__") {
                    let _ = exc.value(py).setattr("item", py_item);
                    let _ = exc_val; // suppress unused warning
                }
                return exc;
            }
        }
    }

    // Fall back to regular error mapping
    map_sdk_error(err, table)
}

/// Map S3 SDK errors to Python exceptions.
pub fn map_s3_error<E, R>(err: SdkError<E, R>, bucket: Option<&str>, key: Option<&str>) -> PyErr
where
    E: std::fmt::Debug + std::fmt::Display,
    R: std::fmt::Debug,
{
    let err_display = err.to_string();
    let err_debug = format!("{:?}", err);

    // Check common errors first
    if let Some(py_err) = map_common_error(&err_debug, AwsService::S3) {
        return py_err;
    }

    // S3-specific errors
    if err_debug.contains("NoSuchBucket") {
        let msg = if let Some(b) = bucket {
            format!("S3 bucket '{}' not found", b)
        } else {
            "S3 bucket not found".to_string()
        };
        return ResourceNotFoundException::new_err(msg);
    }

    if err_debug.contains("NoSuchKey") || err_debug.contains("NotFound") {
        let msg = if let (Some(b), Some(k)) = (bucket, key) {
            format!("S3 object '{}/{}' not found", b, k)
        } else if let Some(k) = key {
            format!("S3 object '{}' not found", k)
        } else {
            "S3 object not found".to_string()
        };
        return ResourceNotFoundException::new_err(msg);
    }

    if err_debug.contains("BucketAlreadyExists") || err_debug.contains("BucketAlreadyOwnedByYou") {
        let msg = if let Some(b) = bucket {
            format!("S3 bucket '{}' already exists", b)
        } else {
            "S3 bucket already exists".to_string()
        };
        return ResourceInUseException::new_err(msg);
    }

    if err_debug.contains("InvalidBucketName") {
        return ValidationException::new_err("Invalid S3 bucket name");
    }

    if err_debug.contains("EntityTooLarge") || err_debug.contains("MaxSizeExceeded") {
        return ValidationException::new_err("S3 object too large");
    }

    if err_debug.contains("InvalidRange") {
        return ValidationException::new_err("Invalid byte range for S3 object");
    }

    // Generic S3 error
    let msg = extract_message(&err_debug).unwrap_or(err_display);
    S3Exception::new_err(format!("S3 operation failed: {}", msg))
}

/// Map KMS SDK errors to Python exceptions.
pub fn map_kms_error<E, R>(err: SdkError<E, R>) -> PyErr
where
    E: std::fmt::Debug + std::fmt::Display,
    R: std::fmt::Debug,
{
    let err_display = err.to_string();
    let err_debug = format!("{:?}", err);

    // Check common errors first
    if let Some(py_err) = map_common_error(&err_debug, AwsService::Kms) {
        return py_err;
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

    // Generic KMS error
    let msg = extract_message(&err_debug).unwrap_or(err_display);
    EncryptionException::new_err(format!("KMS operation failed: {}", msg))
}

// ========== HELPER FUNCTIONS ==========

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
