//! Error types for pydynox.
//!
//! This module maps AWS SDK errors to Python exceptions.
//! Uses typed `SdkError` variant matching — no string parsing of debug output.

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

// ========== TYPED ERROR MAPPING ==========

/// Map non-service `SdkError` variants (dispatch failures, timeouts, etc.).
///
/// Returns `Some(PyErr)` for non-service errors, `None` for `ServiceError`.
fn map_outer_sdk_error<E, R>(err: &SdkError<E, R>, service: AwsService) -> Option<PyErr>
where
    E: std::fmt::Debug,
    R: std::fmt::Debug,
{
    match err {
        SdkError::DispatchFailure(dispatch) => {
            if dispatch.is_timeout() {
                Some(ConnectionException::new_err(format!(
                    "Connection timed out to {}. Check your network or endpoint.",
                    service.name()
                )))
            } else if dispatch.is_io() {
                Some(ConnectionException::new_err(format!(
                    "Connection failed to {} (I/O error). Check if the endpoint is reachable.",
                    service.name()
                )))
            } else {
                Some(ConnectionException::new_err(format!(
                    "Connection failed to {}. Check if the endpoint is reachable.",
                    service.name()
                )))
            }
        }
        SdkError::TimeoutError(_) => Some(ConnectionException::new_err(format!(
            "Connection timed out to {}. Check your network or endpoint.",
            service.name()
        ))),
        SdkError::ConstructionFailure(err) => {
            let msg = format!("{:?}", err);
            if msg.contains("credentials")
                || msg.contains("Credentials")
                || msg.contains("NoCredentialsError")
            {
                Some(CredentialsException::new_err(
                    "No AWS credentials found. Configure credentials via environment variables \
                    (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY), AWS profile, or IAM role.",
                ))
            } else {
                Some(PydynoxException::new_err(format!(
                    "Failed to build request: {}",
                    msg
                )))
            }
        }
        SdkError::ResponseError(err) => Some(PydynoxException::new_err(format!(
            "Invalid response from {}: {:?}",
            service.name(),
            err
        ))),
        SdkError::ServiceError(_) => None,
        _ => Some(PydynoxException::new_err(format!(
            "Unknown error from {}: {:?}",
            service.name(),
            err
        ))),
    }
}

/// Map common service error codes shared across DynamoDB, S3, and KMS.
///
/// Returns `Some(PyErr)` if matched, `None` if the code needs service-specific handling.
fn map_common_service_code(
    code: Option<&str>,
    message: Option<&str>,
    service: AwsService,
) -> Option<PyErr> {
    let code = code?;

    match code {
        "UnrecognizedClientException" => Some(CredentialsException::new_err(
            "Invalid AWS credentials. Check your access key and secret.",
        )),
        "InvalidAccessKeyId" => Some(CredentialsException::new_err(
            "Invalid AWS access key ID. Check your credentials.",
        )),
        "SignatureDoesNotMatch" => Some(CredentialsException::new_err(
            "AWS signature mismatch. Check your secret access key.",
        )),
        "ExpiredTokenException" | "ExpiredToken" => Some(CredentialsException::new_err(
            "AWS credentials have expired. Refresh your session token.",
        )),
        "AccessDeniedException" | "AccessDenied" => {
            let msg = message.unwrap_or("Check your IAM permissions.");
            Some(AccessDeniedException::new_err(format!(
                "Access denied to {}: {}",
                service.name(),
                msg
            )))
        }
        "ProvisionedThroughputExceededException"
        | "LimitExceededException"
        | "RequestLimitExceeded"
        | "Throttling"
        | "ThrottlingException"
        | "SlowDown"
        | "TooManyRequestsException" => {
            Some(ProvisionedThroughputExceededException::new_err(format!(
                "{} request rate too high. Try again with exponential backoff.",
                service.name()
            )))
        }
        _ => None,
    }
}

/// Map a DynamoDB service error code + message to a Python exception.
fn map_dynamodb_code(
    code: Option<&str>,
    message: Option<&str>,
    display: &str,
    table: Option<&str>,
) -> PyErr {
    // Check common cross-service errors first
    if let Some(py_err) = map_common_service_code(code, message, AwsService::DynamoDB) {
        return py_err;
    }

    match code {
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
            let msg = message.unwrap_or(display);
            ValidationException::new_err(msg.to_string())
        }
        Some("ConditionalCheckFailedException") => {
            ConditionalCheckFailedException::new_err("The condition expression evaluated to false")
        }
        Some("TransactionCanceledException") => {
            let msg = message.unwrap_or("Transaction was canceled");
            TransactionCanceledException::new_err(msg.to_string())
        }
        Some("ItemCollectionSizeLimitExceededException") => {
            ValidationException::new_err("Item collection size limit exceeded")
        }
        _ => {
            let msg = message.unwrap_or(display);
            PydynoxException::new_err(msg.to_string())
        }
    }
}

/// Map DynamoDB-specific errors using typed `SdkError` variants.
///
/// For `ServiceError`, uses `ProvideErrorMetadata` to get the error code and message
/// instead of parsing debug strings.
pub fn map_sdk_error<E, R>(err: SdkError<E, R>, table: Option<&str>) -> PyErr
where
    E: aws_sdk_dynamodb::error::ProvideErrorMetadata + std::fmt::Debug + std::fmt::Display,
    R: std::fmt::Debug,
{
    // Check outer SdkError variants first (dispatch, timeout, etc.)
    if let Some(py_err) = map_outer_sdk_error(&err, AwsService::DynamoDB) {
        return py_err;
    }

    // It's a ServiceError — use typed metadata
    if let Some(service_err) = err.as_service_error() {
        let meta = aws_sdk_dynamodb::error::ProvideErrorMetadata::meta(service_err);
        let code = meta.code();
        let message = meta.message();
        let display = service_err.to_string();
        return map_dynamodb_code(code, message, &display, table);
    }

    // Should not reach here (map_outer_sdk_error handles all non-service variants)
    PydynoxException::new_err(format!("Unexpected DynamoDB error: {:?}", err))
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
    E: aws_sdk_dynamodb::error::ProvideErrorMetadata + std::fmt::Debug + std::fmt::Display,
    R: std::fmt::Debug,
{
    // Check outer SdkError variants first
    if let Some(py_err) = map_outer_sdk_error(&err, AwsService::DynamoDB) {
        return py_err;
    }

    // Check for ConditionalCheckFailedException with item
    if let Some(service_err) = err.as_service_error() {
        let meta = aws_sdk_dynamodb::error::ProvideErrorMetadata::meta(service_err);
        let code = meta.code();

        if code == Some("ConditionalCheckFailedException") {
            if let Some(item_data) = item {
                if let Ok(py_item) = attribute_values_to_py_dict(py, item_data) {
                    let exc = ConditionalCheckFailedException::new_err(
                        "The condition expression evaluated to false",
                    );
                    if let Ok(exc_val) = exc.value(py).getattr("__class__") {
                        let _ = exc.value(py).setattr("item", py_item);
                        let _ = exc_val; // suppress unused warning
                    }
                    return exc;
                }
            }
        }
    }

    // Fall back to regular error mapping
    map_sdk_error(err, table)
}

/// Map S3 SDK errors to Python exceptions using typed `SdkError` variants.
pub fn map_s3_error<E, R>(err: SdkError<E, R>, bucket: Option<&str>, key: Option<&str>) -> PyErr
where
    E: aws_sdk_s3::error::ProvideErrorMetadata + std::fmt::Debug + std::fmt::Display,
    R: std::fmt::Debug,
{
    // Check outer SdkError variants first
    if let Some(py_err) = map_outer_sdk_error(&err, AwsService::S3) {
        return py_err;
    }

    // It's a ServiceError — use typed metadata
    if let Some(service_err) = err.as_service_error() {
        let meta = aws_sdk_s3::error::ProvideErrorMetadata::meta(service_err);
        let code = meta.code();
        let message = meta.message();

        // Check common cross-service errors
        if let Some(py_err) = map_common_service_code(code, message, AwsService::S3) {
            return py_err;
        }

        // S3-specific error codes
        return match code {
            Some("NoSuchBucket") => {
                let msg = if let Some(b) = bucket {
                    format!("S3 bucket '{}' not found", b)
                } else {
                    "S3 bucket not found".to_string()
                };
                ResourceNotFoundException::new_err(msg)
            }
            Some("NoSuchKey") | Some("NotFound") => {
                let msg = if let (Some(b), Some(k)) = (bucket, key) {
                    format!("S3 object '{}/{}' not found", b, k)
                } else if let Some(k) = key {
                    format!("S3 object '{}' not found", k)
                } else {
                    "S3 object not found".to_string()
                };
                ResourceNotFoundException::new_err(msg)
            }
            Some("BucketAlreadyExists") | Some("BucketAlreadyOwnedByYou") => {
                let msg = if let Some(b) = bucket {
                    format!("S3 bucket '{}' already exists", b)
                } else {
                    "S3 bucket already exists".to_string()
                };
                ResourceInUseException::new_err(msg)
            }
            Some("InvalidBucketName") => ValidationException::new_err("Invalid S3 bucket name"),
            Some("EntityTooLarge") | Some("MaxSizeExceeded") => {
                ValidationException::new_err("S3 object too large")
            }
            Some("InvalidRange") => {
                ValidationException::new_err("Invalid byte range for S3 object")
            }
            _ => {
                let msg = message
                    .map(|m| m.to_string())
                    .unwrap_or_else(|| service_err.to_string());
                S3Exception::new_err(format!("S3 operation failed: {}", msg))
            }
        };
    }

    PydynoxException::new_err(format!("Unexpected S3 error: {:?}", err))
}

/// Map KMS SDK errors to Python exceptions using typed `SdkError` variants.
pub fn map_kms_error<E, R>(err: SdkError<E, R>) -> PyErr
where
    E: aws_sdk_kms::error::ProvideErrorMetadata + std::fmt::Debug + std::fmt::Display,
    R: std::fmt::Debug,
{
    // Check outer SdkError variants first
    if let Some(py_err) = map_outer_sdk_error(&err, AwsService::Kms) {
        return py_err;
    }

    // It's a ServiceError — use typed metadata
    if let Some(service_err) = err.as_service_error() {
        let meta = aws_sdk_kms::error::ProvideErrorMetadata::meta(service_err);
        let code = meta.code();
        let message = meta.message();

        // Check common cross-service errors
        if let Some(py_err) = map_common_service_code(code, message, AwsService::Kms) {
            return py_err;
        }

        // KMS-specific error codes
        return match code {
            Some("NotFoundException") => {
                EncryptionException::new_err("KMS key not found. Check the key ID or alias.")
            }
            Some("DisabledException") => EncryptionException::new_err("KMS key is disabled."),
            Some("InvalidKeyUsageException") => {
                EncryptionException::new_err("KMS key cannot be used for this operation.")
            }
            Some("KeyUnavailableException") => {
                EncryptionException::new_err("KMS key is not available. Try again later.")
            }
            Some("InvalidCiphertextException") => {
                EncryptionException::new_err("Invalid ciphertext. Data may be corrupted.")
            }
            Some("IncorrectKeyException") => {
                EncryptionException::new_err("Wrong KMS key used for decryption.")
            }
            Some("InvalidGrantTokenException") => {
                EncryptionException::new_err("Invalid grant token.")
            }
            _ => {
                let msg = message
                    .map(|m| m.to_string())
                    .unwrap_or_else(|| service_err.to_string());
                EncryptionException::new_err(format!("KMS operation failed: {}", msg))
            }
        };
    }

    PydynoxException::new_err(format!("Unexpected KMS error: {:?}", err))
}
