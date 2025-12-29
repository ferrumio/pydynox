//! Error types for pydynox.
//!
//! This module maps AWS SDK errors to Python exceptions.
//! Uses a single mapping function to avoid code duplication.

use aws_sdk_dynamodb::error::SdkError;
use pyo3::create_exception;
use pyo3::exceptions::PyException;
use pyo3::prelude::*;

// Create Python exception classes
create_exception!(pydynox, PydynoxError, PyException);
create_exception!(pydynox, TableNotFoundError, PydynoxError);
create_exception!(pydynox, TableAlreadyExistsError, PydynoxError);
create_exception!(pydynox, ValidationError, PydynoxError);
create_exception!(pydynox, ConditionCheckFailedError, PydynoxError);
create_exception!(pydynox, TransactionCanceledError, PydynoxError);
create_exception!(pydynox, ThrottlingError, PydynoxError);
create_exception!(pydynox, AccessDeniedError, PydynoxError);
create_exception!(pydynox, CredentialsError, PydynoxError);
create_exception!(pydynox, SerializationError, PydynoxError);

/// Register exception classes with the Python module.
pub fn register_exceptions(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("PydynoxError", m.py().get_type::<PydynoxError>())?;
    m.add(
        "TableNotFoundError",
        m.py().get_type::<TableNotFoundError>(),
    )?;
    m.add(
        "TableAlreadyExistsError",
        m.py().get_type::<TableAlreadyExistsError>(),
    )?;
    m.add("ValidationError", m.py().get_type::<ValidationError>())?;
    m.add(
        "ConditionCheckFailedError",
        m.py().get_type::<ConditionCheckFailedError>(),
    )?;
    m.add(
        "TransactionCanceledError",
        m.py().get_type::<TransactionCanceledError>(),
    )?;
    m.add("ThrottlingError", m.py().get_type::<ThrottlingError>())?;
    m.add("AccessDeniedError", m.py().get_type::<AccessDeniedError>())?;
    m.add("CredentialsError", m.py().get_type::<CredentialsError>())?;
    m.add(
        "SerializationError",
        m.py().get_type::<SerializationError>(),
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

    // Check for credential errors first (these are dispatch failures, not service errors)
    if err_debug.contains("NoCredentialsError")
        || err_debug.contains("no credentials")
        || err_debug.contains("No credentials")
        || err_debug.contains("CredentialsError")
        || err_debug.contains("failed to load credentials")
    {
        return CredentialsError::new_err(
            "No AWS credentials found. Configure credentials via environment variables \
            (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY), AWS profile, or IAM role.",
        );
    }

    if err_debug.contains("InvalidAccessKeyId") || err_debug.contains("invalid access key") {
        return CredentialsError::new_err("Invalid AWS access key ID. Check your credentials.");
    }

    if err_debug.contains("SignatureDoesNotMatch") {
        return CredentialsError::new_err("AWS signature mismatch. Check your secret access key.");
    }

    if err_debug.contains("ExpiredToken") || err_debug.contains("expired") {
        return CredentialsError::new_err(
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
            TableNotFoundError::new_err(msg)
        }
        Some("ResourceInUseException") => {
            let msg = if let Some(t) = table {
                format!("Table '{}' already exists", t)
            } else {
                "Resource already in use".to_string()
            };
            TableAlreadyExistsError::new_err(msg)
        }
        Some("ValidationException") => {
            // Try to extract the actual validation message
            let msg = extract_message(&err_debug).unwrap_or(err_display);
            ValidationError::new_err(msg)
        }
        Some("ConditionalCheckFailedException") => {
            ConditionCheckFailedError::new_err("The condition expression evaluated to false")
        }
        Some("TransactionCanceledException") => {
            let reasons = extract_cancellation_reasons(&err_debug);
            let msg = if reasons.is_empty() {
                "Transaction was canceled".to_string()
            } else {
                format!("Transaction was canceled: {}", reasons.join("; "))
            };
            TransactionCanceledError::new_err(msg)
        }
        Some("ProvisionedThroughputExceededException") | Some("ThrottlingException") => {
            ThrottlingError::new_err("Request rate too high. Try again with exponential backoff.")
        }
        Some("AccessDeniedException") => {
            let msg = extract_message(&err_debug)
                .unwrap_or_else(|| "Access denied. Check your IAM permissions.".to_string());
            AccessDeniedError::new_err(msg)
        }
        Some("UnrecognizedClientException") => {
            CredentialsError::new_err("Invalid AWS credentials. Check your access key and secret.")
        }
        Some("ItemCollectionSizeLimitExceededException") => {
            ValidationError::new_err("Item collection size limit exceeded")
        }
        Some("RequestLimitExceeded") => {
            ThrottlingError::new_err("Request limit exceeded. Try again later.")
        }
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
            PydynoxError::new_err(msg)
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
        "ThrottlingException",
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
