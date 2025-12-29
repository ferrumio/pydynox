//! Table management operations for DynamoDB.
//!
//! Provides functions to create, delete, and check table status.
//! Useful for local development and testing with moto/localstack.

use aws_sdk_dynamodb::types::{
    AttributeDefinition, BillingMode, KeySchemaElement, KeyType, ScalarAttributeType,
    SseSpecification, SseType, TableClass, TableStatus,
};
use aws_sdk_dynamodb::Client;
use pyo3::prelude::*;
use std::sync::Arc;
use std::time::Duration;
use tokio::runtime::Runtime;

use crate::errors::{map_sdk_error, ValidationError};

/// Create a new DynamoDB table.
///
/// # Arguments
///
/// * `client` - The DynamoDB client
/// * `runtime` - The Tokio runtime
/// * `table_name` - Name of the table to create
/// * `hash_key_name` - Name of the hash key attribute
/// * `hash_key_type` - Type of the hash key ("S", "N", or "B")
/// * `range_key_name` - Optional name of the range key attribute
/// * `range_key_type` - Optional type of the range key
/// * `billing_mode` - "PAY_PER_REQUEST" or "PROVISIONED"
/// * `read_capacity` - Read capacity units (only for PROVISIONED)
/// * `write_capacity` - Write capacity units (only for PROVISIONED)
/// * `table_class` - "STANDARD" or "STANDARD_INFREQUENT_ACCESS"
/// * `encryption` - "AWS_OWNED", "AWS_MANAGED", or "CUSTOMER_MANAGED"
/// * `kms_key_id` - KMS key ARN (required when encryption is "CUSTOMER_MANAGED")
#[allow(clippy::too_many_arguments)]
pub fn create_table(
    client: &Client,
    runtime: &Arc<Runtime>,
    table_name: &str,
    hash_key_name: &str,
    hash_key_type: &str,
    range_key_name: Option<&str>,
    range_key_type: Option<&str>,
    billing_mode: &str,
    read_capacity: Option<i64>,
    write_capacity: Option<i64>,
    table_class: Option<&str>,
    encryption: Option<&str>,
    kms_key_id: Option<&str>,
) -> PyResult<()> {
    let hash_attr_type = parse_attribute_type(hash_key_type)?;

    // Build attribute definitions
    let mut attribute_definitions = vec![AttributeDefinition::builder()
        .attribute_name(hash_key_name)
        .attribute_type(hash_attr_type)
        .build()
        .map_err(|e| ValidationError::new_err(format!("Invalid attribute definition: {}", e)))?];

    // Build key schema
    let mut key_schema = vec![KeySchemaElement::builder()
        .attribute_name(hash_key_name)
        .key_type(KeyType::Hash)
        .build()
        .map_err(|e| ValidationError::new_err(format!("Invalid key schema: {}", e)))?];

    // Add range key if provided
    if let (Some(rk_name), Some(rk_type)) = (range_key_name, range_key_type) {
        let range_attr_type = parse_attribute_type(rk_type)?;

        attribute_definitions.push(
            AttributeDefinition::builder()
                .attribute_name(rk_name)
                .attribute_type(range_attr_type)
                .build()
                .map_err(|e| {
                    ValidationError::new_err(format!("Invalid attribute definition: {}", e))
                })?,
        );

        key_schema.push(
            KeySchemaElement::builder()
                .attribute_name(rk_name)
                .key_type(KeyType::Range)
                .build()
                .map_err(|e| ValidationError::new_err(format!("Invalid key schema: {}", e)))?,
        );
    }

    // Parse billing mode
    let billing = parse_billing_mode(billing_mode)?;

    let client = client.clone();
    let table_name = table_name.to_string();

    runtime.block_on(async {
        let mut request = client
            .create_table()
            .table_name(&table_name)
            .set_attribute_definitions(Some(attribute_definitions))
            .set_key_schema(Some(key_schema))
            .billing_mode(billing.clone());

        // Add provisioned throughput if using PROVISIONED billing
        if billing == BillingMode::Provisioned {
            let rcu = read_capacity.unwrap_or(5);
            let wcu = write_capacity.unwrap_or(5);

            request = request.provisioned_throughput(
                aws_sdk_dynamodb::types::ProvisionedThroughput::builder()
                    .read_capacity_units(rcu)
                    .write_capacity_units(wcu)
                    .build()
                    .map_err(|e| {
                        ValidationError::new_err(format!("Invalid provisioned throughput: {}", e))
                    })?,
            );
        }

        // Add table class if specified
        if let Some(tc) = table_class {
            let class = parse_table_class(tc)?;
            request = request.table_class(class);
        }

        // Add encryption if specified
        if let Some(enc) = encryption {
            let sse_spec = build_sse_specification(enc, kms_key_id)?;
            request = request.sse_specification(sse_spec);
        }

        request
            .send()
            .await
            .map_err(|e| map_sdk_error(e, Some(&table_name)))?;

        Ok(())
    })
}

/// Check if a table exists.
///
/// # Arguments
///
/// * `client` - The DynamoDB client
/// * `runtime` - The Tokio runtime
/// * `table_name` - Name of the table to check
///
/// # Returns
///
/// True if the table exists, false otherwise.
pub fn table_exists(client: &Client, runtime: &Arc<Runtime>, table_name: &str) -> PyResult<bool> {
    let client = client.clone();
    let table_name = table_name.to_string();

    runtime.block_on(async {
        match client.describe_table().table_name(&table_name).send().await {
            Ok(_) => Ok(true),
            Err(e) => {
                let service_error = e.into_service_error();
                if service_error.is_resource_not_found_exception() {
                    Ok(false)
                } else {
                    // Re-wrap as SdkError for map_sdk_error
                    Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!(
                        "Failed to check table '{}': {}",
                        table_name, service_error
                    )))
                }
            }
        }
    })
}

/// Delete a table.
///
/// # Arguments
///
/// * `client` - The DynamoDB client
/// * `runtime` - The Tokio runtime
/// * `table_name` - Name of the table to delete
pub fn delete_table(client: &Client, runtime: &Arc<Runtime>, table_name: &str) -> PyResult<()> {
    let client = client.clone();
    let table_name = table_name.to_string();

    runtime.block_on(async {
        client
            .delete_table()
            .table_name(&table_name)
            .send()
            .await
            .map_err(|e| map_sdk_error(e, Some(&table_name)))?;

        Ok(())
    })
}

/// Wait for a table to become active.
///
/// Polls the table status until it becomes ACTIVE or times out.
///
/// # Arguments
///
/// * `client` - The DynamoDB client
/// * `runtime` - The Tokio runtime
/// * `table_name` - Name of the table to wait for
/// * `timeout_seconds` - Maximum time to wait (default: 60)
pub fn wait_for_table_active(
    client: &Client,
    runtime: &Arc<Runtime>,
    table_name: &str,
    timeout_seconds: Option<u64>,
) -> PyResult<()> {
    let client = client.clone();
    let table_name = table_name.to_string();
    let timeout = timeout_seconds.unwrap_or(60);

    runtime.block_on(async {
        let start = std::time::Instant::now();
        let poll_interval = Duration::from_millis(500);

        loop {
            if start.elapsed().as_secs() > timeout {
                return Err(PyErr::new::<pyo3::exceptions::PyTimeoutError, _>(format!(
                    "Timeout waiting for table '{}' to become active",
                    table_name
                )));
            }

            let result = client.describe_table().table_name(&table_name).send().await;

            match result {
                Ok(response) => {
                    if let Some(table) = response.table() {
                        if table.table_status() == Some(&TableStatus::Active) {
                            return Ok(());
                        }
                    }
                }
                Err(e) => {
                    let service_error = e.into_service_error();
                    if !service_error.is_resource_not_found_exception() {
                        return Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!(
                            "Failed to describe table '{}': {}",
                            table_name, service_error
                        )));
                    }
                }
            }

            tokio::time::sleep(poll_interval).await;
        }
    })
}

/// Parse a string attribute type to ScalarAttributeType.
fn parse_attribute_type(type_str: &str) -> PyResult<ScalarAttributeType> {
    match type_str.to_uppercase().as_str() {
        "S" | "STRING" => Ok(ScalarAttributeType::S),
        "N" | "NUMBER" => Ok(ScalarAttributeType::N),
        "B" | "BINARY" => Ok(ScalarAttributeType::B),
        _ => Err(ValidationError::new_err(format!(
            "Invalid attribute type: '{}'. Use 'S' (string), 'N' (number), or 'B' (binary)",
            type_str
        ))),
    }
}

/// Parse a string billing mode to BillingMode.
fn parse_billing_mode(mode_str: &str) -> PyResult<BillingMode> {
    match mode_str.to_uppercase().as_str() {
        "PAY_PER_REQUEST" => Ok(BillingMode::PayPerRequest),
        "PROVISIONED" => Ok(BillingMode::Provisioned),
        _ => Err(ValidationError::new_err(format!(
            "Invalid billing_mode: '{}'. Use 'PAY_PER_REQUEST' or 'PROVISIONED'",
            mode_str
        ))),
    }
}

/// Parse a string table class to TableClass.
fn parse_table_class(class_str: &str) -> PyResult<TableClass> {
    match class_str.to_uppercase().as_str() {
        "STANDARD" => Ok(TableClass::Standard),
        "STANDARD_INFREQUENT_ACCESS" | "STANDARD_IA" => Ok(TableClass::StandardInfrequentAccess),
        _ => Err(ValidationError::new_err(format!(
            "Invalid table_class: '{}'. Use 'STANDARD' or 'STANDARD_INFREQUENT_ACCESS'",
            class_str
        ))),
    }
}

/// Build SSE specification from encryption type and optional KMS key.
///
/// Accepts:
/// - "AWS_OWNED" - Default encryption with AWS owned keys (no extra cost)
/// - "AWS_MANAGED" - Encryption with AWS managed KMS key (KMS charges apply)
/// - "CUSTOMER_MANAGED" - Encryption with customer KMS key (requires kms_key_id)
fn build_sse_specification(
    encryption: &str,
    kms_key_id: Option<&str>,
) -> PyResult<SseSpecification> {
    match encryption.to_uppercase().as_str() {
        "AWS_OWNED" => Ok(SseSpecification::builder().enabled(true).build()),
        "AWS_MANAGED" => Ok(SseSpecification::builder()
            .enabled(true)
            .sse_type(SseType::Kms)
            .build()),
        "CUSTOMER_MANAGED" => {
            let key_id = kms_key_id.ok_or_else(|| {
                ValidationError::new_err(
                    "kms_key_id is required when encryption is 'CUSTOMER_MANAGED'",
                )
            })?;
            Ok(SseSpecification::builder()
                .enabled(true)
                .sse_type(SseType::Kms)
                .kms_master_key_id(key_id)
                .build())
        }
        _ => Err(ValidationError::new_err(format!(
            "Invalid encryption: '{}'. Use 'AWS_OWNED', 'AWS_MANAGED', or 'CUSTOMER_MANAGED'",
            encryption
        ))),
    }
}
