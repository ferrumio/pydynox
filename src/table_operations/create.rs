//! Table creation operation.

use aws_sdk_dynamodb::types::{
    AttributeDefinition, BillingMode, GlobalSecondaryIndex, KeySchemaElement, KeyType,
    LocalSecondaryIndex, Projection, ProjectionType, ScalarAttributeType, SseSpecification,
    SseType, TableClass,
};
use aws_sdk_dynamodb::Client;
use pyo3::prelude::*;
use std::collections::HashSet;
use std::sync::Arc;
use tokio::runtime::Runtime;

use super::gsi::GsiDefinition;
use super::lsi::LsiDefinition;
use super::wait::{execute_wait_for_table_active, sync_wait_for_table_active};
use crate::errors::{map_sdk_error, ValidationException};

/// Prepared create table request (converted before async).
pub struct PreparedCreateTable {
    pub table_name: String,
    pub attribute_definitions: Vec<AttributeDefinition>,
    pub key_schema: Vec<KeySchemaElement>,
    pub billing: BillingMode,
    pub read_capacity: Option<i64>,
    pub write_capacity: Option<i64>,
    pub table_class: Option<TableClass>,
    pub sse_spec: Option<SseSpecification>,
    pub gsi_list: Vec<GlobalSecondaryIndex>,
    pub lsi_list: Vec<LocalSecondaryIndex>,
    pub wait: bool,
}

/// Prepare create table request - validates and builds all AWS types.
#[allow(clippy::too_many_arguments)]
pub fn prepare_create_table(
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
    lsis: Option<Vec<LsiDefinition>>,
    wait: bool,
) -> PyResult<PreparedCreateTable> {
    let hash_attr_type = parse_attribute_type(hash_key_type)?;

    // Track all attribute names to avoid duplicates
    let mut defined_attrs: HashSet<String> = HashSet::new();

    // Build attribute definitions
    let mut attribute_definitions = vec![AttributeDefinition::builder()
        .attribute_name(hash_key_name)
        .attribute_type(hash_attr_type)
        .build()
        .map_err(|e| {
            ValidationException::new_err(format!("Invalid attribute definition: {}", e))
        })?];
    defined_attrs.insert(hash_key_name.to_string());

    // Build key schema
    let mut key_schema = vec![KeySchemaElement::builder()
        .attribute_name(hash_key_name)
        .key_type(KeyType::Hash)
        .build()
        .map_err(|e| ValidationException::new_err(format!("Invalid key schema: {}", e)))?];

    // Add range key if provided
    if let (Some(rk_name), Some(rk_type)) = (range_key_name, range_key_type) {
        let range_attr_type = parse_attribute_type(rk_type)?;

        attribute_definitions.push(
            AttributeDefinition::builder()
                .attribute_name(rk_name)
                .attribute_type(range_attr_type)
                .build()
                .map_err(|e| {
                    ValidationException::new_err(format!("Invalid attribute definition: {}", e))
                })?,
        );
        defined_attrs.insert(rk_name.to_string());

        key_schema.push(
            KeySchemaElement::builder()
                .attribute_name(rk_name)
                .key_type(KeyType::Range)
                .build()
                .map_err(|e| ValidationException::new_err(format!("Invalid key schema: {}", e)))?,
        );
    }

    // Build GSIs if provided
    let mut gsi_list: Vec<GlobalSecondaryIndex> = Vec::new();
    if let Some(gsi_defs) = gsis {
        for gsi in gsi_defs {
            let mut gsi_key_schema: Vec<KeySchemaElement> = Vec::new();

            // Add all hash key attributes
            for key_attr in &gsi.hash_keys {
                if !defined_attrs.contains(&key_attr.name) {
                    let attr_type = parse_attribute_type(&key_attr.attr_type)?;
                    attribute_definitions.push(
                        AttributeDefinition::builder()
                            .attribute_name(&key_attr.name)
                            .attribute_type(attr_type)
                            .build()
                            .map_err(|e| {
                                ValidationException::new_err(format!(
                                    "Invalid GSI attribute: {}",
                                    e
                                ))
                            })?,
                    );
                    defined_attrs.insert(key_attr.name.clone());
                }

                gsi_key_schema.push(
                    KeySchemaElement::builder()
                        .attribute_name(&key_attr.name)
                        .key_type(KeyType::Hash)
                        .build()
                        .map_err(|e| {
                            ValidationException::new_err(format!("Invalid GSI key schema: {}", e))
                        })?,
                );
            }

            // Add all range key attributes
            for key_attr in &gsi.range_keys {
                if !defined_attrs.contains(&key_attr.name) {
                    let attr_type = parse_attribute_type(&key_attr.attr_type)?;
                    attribute_definitions.push(
                        AttributeDefinition::builder()
                            .attribute_name(&key_attr.name)
                            .attribute_type(attr_type)
                            .build()
                            .map_err(|e| {
                                ValidationException::new_err(format!(
                                    "Invalid GSI attribute: {}",
                                    e
                                ))
                            })?,
                    );
                    defined_attrs.insert(key_attr.name.clone());
                }

                gsi_key_schema.push(
                    KeySchemaElement::builder()
                        .attribute_name(&key_attr.name)
                        .key_type(KeyType::Range)
                        .build()
                        .map_err(|e| {
                            ValidationException::new_err(format!("Invalid GSI key schema: {}", e))
                        })?,
                );
            }

            let projection = build_projection(&gsi.projection, gsi.non_key_attributes.as_deref())?;

            let gsi_builder = GlobalSecondaryIndex::builder()
                .index_name(&gsi.index_name)
                .set_key_schema(Some(gsi_key_schema))
                .projection(projection)
                .build()
                .map_err(|e| ValidationException::new_err(format!("Invalid GSI: {}", e)))?;

            gsi_list.push(gsi_builder);
        }
    }

    // Build LSIs if provided
    let mut lsi_list: Vec<LocalSecondaryIndex> = Vec::new();
    if let Some(lsi_defs) = lsis {
        for lsi in lsi_defs {
            let mut lsi_key_schema: Vec<KeySchemaElement> = Vec::new();

            // LSI shares table's hash key
            lsi_key_schema.push(
                KeySchemaElement::builder()
                    .attribute_name(hash_key_name)
                    .key_type(KeyType::Hash)
                    .build()
                    .map_err(|e| {
                        ValidationException::new_err(format!("Invalid LSI key schema: {}", e))
                    })?,
            );

            // Add LSI's range key
            if !defined_attrs.contains(&lsi.range_key_name) {
                let attr_type = parse_attribute_type(&lsi.range_key_type)?;
                attribute_definitions.push(
                    AttributeDefinition::builder()
                        .attribute_name(&lsi.range_key_name)
                        .attribute_type(attr_type)
                        .build()
                        .map_err(|e| {
                            ValidationException::new_err(format!("Invalid LSI attribute: {}", e))
                        })?,
                );
                defined_attrs.insert(lsi.range_key_name.clone());
            }

            lsi_key_schema.push(
                KeySchemaElement::builder()
                    .attribute_name(&lsi.range_key_name)
                    .key_type(KeyType::Range)
                    .build()
                    .map_err(|e| {
                        ValidationException::new_err(format!("Invalid LSI key schema: {}", e))
                    })?,
            );

            let projection = build_projection(&lsi.projection, lsi.non_key_attributes.as_deref())?;

            let lsi_builder = LocalSecondaryIndex::builder()
                .index_name(&lsi.index_name)
                .set_key_schema(Some(lsi_key_schema))
                .projection(projection)
                .build()
                .map_err(|e| ValidationException::new_err(format!("Invalid LSI: {}", e)))?;

            lsi_list.push(lsi_builder);
        }
    }

    let billing = parse_billing_mode(billing_mode)?;

    let tc = match table_class {
        Some(tc) => Some(parse_table_class(tc)?),
        None => None,
    };

    let sse_spec = match encryption {
        Some(enc) => Some(build_sse_specification(enc, kms_key_id)?),
        None => None,
    };

    Ok(PreparedCreateTable {
        table_name: table_name.to_string(),
        attribute_definitions,
        key_schema,
        billing,
        read_capacity,
        write_capacity,
        table_class: tc,
        sse_spec,
        gsi_list,
        lsi_list,
        wait,
    })
}

/// Execute create table asynchronously.
pub async fn execute_create_table(client: Client, prepared: PreparedCreateTable) -> PyResult<()> {
    let mut request = client
        .create_table()
        .table_name(&prepared.table_name)
        .set_attribute_definitions(Some(prepared.attribute_definitions))
        .set_key_schema(Some(prepared.key_schema))
        .billing_mode(prepared.billing.clone());

    if !prepared.gsi_list.is_empty() {
        request = request.set_global_secondary_indexes(Some(prepared.gsi_list));
    }

    if !prepared.lsi_list.is_empty() {
        request = request.set_local_secondary_indexes(Some(prepared.lsi_list));
    }

    if prepared.billing == BillingMode::Provisioned {
        let rcu = prepared.read_capacity.unwrap_or(5);
        let wcu = prepared.write_capacity.unwrap_or(5);

        request = request.provisioned_throughput(
            aws_sdk_dynamodb::types::ProvisionedThroughput::builder()
                .read_capacity_units(rcu)
                .write_capacity_units(wcu)
                .build()
                .map_err(|e| {
                    ValidationException::new_err(format!("Invalid provisioned throughput: {}", e))
                })?,
        );
    }

    if let Some(class) = prepared.table_class {
        request = request.table_class(class);
    }

    if let Some(sse) = prepared.sse_spec {
        request = request.sse_specification(sse);
    }

    request
        .send()
        .await
        .map_err(|e| map_sdk_error(e, Some(&prepared.table_name)))?;

    // Wait for table to become active if requested
    if prepared.wait {
        execute_wait_for_table_active(client, &prepared.table_name, None).await?;
    }

    Ok(())
}

/// Async create_table - returns a Python awaitable.
#[allow(clippy::too_many_arguments)]
pub fn create_table<'py>(
    py: Python<'py>,
    client: Client,
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
    lsis: Option<Vec<LsiDefinition>>,
    wait: bool,
) -> PyResult<Bound<'py, PyAny>> {
    let prepared = prepare_create_table(
        table_name,
        hash_key_name,
        hash_key_type,
        range_key_name,
        range_key_type,
        billing_mode,
        read_capacity,
        write_capacity,
        table_class,
        encryption,
        kms_key_id,
        gsis,
        lsis,
        wait,
    )?;

    pyo3_async_runtimes::tokio::future_into_py(py, async move {
        execute_create_table(client, prepared).await
    })
}

/// Sync create_table - blocks until complete.
#[allow(clippy::too_many_arguments)]
pub fn sync_create_table(
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
    lsis: Option<Vec<LsiDefinition>>,
    wait: bool,
) -> PyResult<()> {
    let prepared = prepare_create_table(
        table_name,
        hash_key_name,
        hash_key_type,
        range_key_name,
        range_key_type,
        billing_mode,
        read_capacity,
        write_capacity,
        table_class,
        encryption,
        kms_key_id,
        gsis,
        lsis,
        false, // Don't wait in the async part
    )?;

    let client_clone = client.clone();
    let table_name_owned = table_name.to_string();

    runtime.block_on(async { execute_create_table(client_clone, prepared).await })?;

    // Wait for table to become active if requested (sync version)
    if wait {
        sync_wait_for_table_active(client, runtime, &table_name_owned, None)?;
    }

    Ok(())
}

/// Build projection for GSI/LSI.
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
                ValidationException::new_err(
                    "non_key_attributes required when projection is 'INCLUDE'",
                )
            })?;
            Ok(Projection::builder()
                .projection_type(ProjectionType::Include)
                .set_non_key_attributes(Some(attrs.to_vec()))
                .build())
        }
        _ => Err(ValidationException::new_err(format!(
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
        _ => Err(ValidationException::new_err(format!(
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
        _ => Err(ValidationException::new_err(format!(
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
        _ => Err(ValidationException::new_err(format!(
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
                ValidationException::new_err(
                    "kms_key_id is required when encryption is 'CUSTOMER_MANAGED'",
                )
            })?;
            Ok(SseSpecification::builder()
                .enabled(true)
                .sse_type(SseType::Kms)
                .kms_master_key_id(key_id)
                .build())
        }
        _ => Err(ValidationException::new_err(format!(
            "Invalid encryption: '{}'. Use 'AWS_OWNED', 'AWS_MANAGED', or 'CUSTOMER_MANAGED'",
            encryption
        ))),
    }
}
