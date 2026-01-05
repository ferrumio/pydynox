//! Table creation operation.

use aws_sdk_dynamodb::types::{
    AttributeDefinition, BillingMode, GlobalSecondaryIndex, KeySchemaElement, KeyType, Projection,
    ProjectionType, ScalarAttributeType, SseSpecification, SseType, TableClass,
};
use aws_sdk_dynamodb::Client;
use pyo3::prelude::*;
use std::collections::HashSet;
use std::sync::Arc;
use tokio::runtime::Runtime;

use super::gsi::GsiDefinition;
use super::wait::wait_for_table_active;
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
/// * `gsis` - Optional list of GSI definitions
/// * `wait` - Wait for table to become active
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
    gsis: Option<Vec<GsiDefinition>>,
    wait: bool,
) -> PyResult<()> {
    let hash_attr_type = parse_attribute_type(hash_key_type)?;

    // Track all attribute names to avoid duplicates
    let mut defined_attrs: HashSet<String> = HashSet::new();

    // Build attribute definitions
    let mut attribute_definitions = vec![AttributeDefinition::builder()
        .attribute_name(hash_key_name)
        .attribute_type(hash_attr_type)
        .build()
        .map_err(|e| ValidationError::new_err(format!("Invalid attribute definition: {}", e)))?];
    defined_attrs.insert(hash_key_name.to_string());

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
        defined_attrs.insert(rk_name.to_string());

        key_schema.push(
            KeySchemaElement::builder()
                .attribute_name(rk_name)
                .key_type(KeyType::Range)
                .build()
                .map_err(|e| ValidationError::new_err(format!("Invalid key schema: {}", e)))?,
        );
    }

    // Build GSIs if provided
    let mut gsi_list: Vec<GlobalSecondaryIndex> = Vec::new();
    if let Some(gsi_defs) = gsis {
        for gsi in gsi_defs {
            let mut gsi_key_schema: Vec<KeySchemaElement> = Vec::new();

            // Add all hash key attributes
            for key_attr in &gsi.hash_keys {
                // Add attribute definition if not already defined
                if !defined_attrs.contains(&key_attr.name) {
                    let attr_type = parse_attribute_type(&key_attr.attr_type)?;
                    attribute_definitions.push(
                        AttributeDefinition::builder()
                            .attribute_name(&key_attr.name)
                            .attribute_type(attr_type)
                            .build()
                            .map_err(|e| {
                                ValidationError::new_err(format!("Invalid GSI attribute: {}", e))
                            })?,
                    );
                    defined_attrs.insert(key_attr.name.clone());
                }

                // Add to key schema
                gsi_key_schema.push(
                    KeySchemaElement::builder()
                        .attribute_name(&key_attr.name)
                        .key_type(KeyType::Hash)
                        .build()
                        .map_err(|e| {
                            ValidationError::new_err(format!("Invalid GSI key schema: {}", e))
                        })?,
                );
            }

            // Add all range key attributes
            for key_attr in &gsi.range_keys {
                // Add attribute definition if not already defined
                if !defined_attrs.contains(&key_attr.name) {
                    let attr_type = parse_attribute_type(&key_attr.attr_type)?;
                    attribute_definitions.push(
                        AttributeDefinition::builder()
                            .attribute_name(&key_attr.name)
                            .attribute_type(attr_type)
                            .build()
                            .map_err(|e| {
                                ValidationError::new_err(format!("Invalid GSI attribute: {}", e))
                            })?,
                    );
                    defined_attrs.insert(key_attr.name.clone());
                }

                // Add to key schema
                gsi_key_schema.push(
                    KeySchemaElement::builder()
                        .attribute_name(&key_attr.name)
                        .key_type(KeyType::Range)
                        .build()
                        .map_err(|e| {
                            ValidationError::new_err(format!("Invalid GSI key schema: {}", e))
                        })?,
                );
            }

            // Build projection
            let projection = build_projection(&gsi.projection, gsi.non_key_attributes.as_deref())?;

            // Build GSI
            let gsi_builder = GlobalSecondaryIndex::builder()
                .index_name(&gsi.index_name)
                .set_key_schema(Some(gsi_key_schema))
                .projection(projection)
                .build()
                .map_err(|e| ValidationError::new_err(format!("Invalid GSI: {}", e)))?;

            gsi_list.push(gsi_builder);
        }
    }

    // Parse billing mode
    let billing = parse_billing_mode(billing_mode)?;

    let client_clone = client.clone();
    let table_name_owned = table_name.to_string();

    runtime.block_on(async {
        let mut request = client_clone
            .create_table()
            .table_name(&table_name_owned)
            .set_attribute_definitions(Some(attribute_definitions))
            .set_key_schema(Some(key_schema))
            .billing_mode(billing.clone());

        // Add GSIs if any
        if !gsi_list.is_empty() {
            request = request.set_global_secondary_indexes(Some(gsi_list));
        }

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
            .map_err(|e| map_sdk_error(e, Some(&table_name_owned)))?;

        Ok::<(), PyErr>(())
    })?;

    // Wait for table to become active if requested
    if wait {
        wait_for_table_active(client, runtime, table_name, None)?;
    }

    Ok(())
}

/// Build projection for GSI.
fn build_projection(
    projection_type: &str,
    non_key_attributes: Option<&[String]>,
) -> PyResult<Projection> {
    match projection_type.to_uppercase().as_str() {
        "ALL" => Ok(Projection::builder()
            .projection_type(ProjectionType::All)
            .build()),
        "KEYS_ONLY" => Ok(Projection::builder()
            .projection_type(ProjectionType::KeysOnly)
            .build()),
        "INCLUDE" => {
            let attrs = non_key_attributes.ok_or_else(|| {
                ValidationError::new_err("non_key_attributes required when projection is 'INCLUDE'")
            })?;
            Ok(Projection::builder()
                .projection_type(ProjectionType::Include)
                .set_non_key_attributes(Some(attrs.to_vec()))
                .build())
        }
        _ => Err(ValidationError::new_err(format!(
            "Invalid projection: '{}'. Use 'ALL', 'KEYS_ONLY', or 'INCLUDE'",
            projection_type
        ))),
    }
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
