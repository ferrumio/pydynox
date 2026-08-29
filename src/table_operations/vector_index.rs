//! Vector index definitions and lifecycle operations.

use aws_sdk_dynamodb::Client;
use aws_sdk_dynamodb::types::{
    CreateVectorIndexAction, DeleteVectorIndexAction, Projection, ProjectionType,
    SearchSchemaElement, SearchSchemaElementType, VectorAttributeDefinition,
    VectorDistanceFunction, VectorIndex, VectorIndexDescription, VectorIndexUpdate,
};
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::runtime::Runtime;

use crate::errors::{ValidationException, map_sdk_error};

#[derive(Clone, Debug)]
pub struct VectorIndexDefinition {
    pub index_name: String,
    pub vector_attribute: String,
    pub dimensions: i64,
    pub distance_function: String,
    pub partition_key: Option<String>,
    pub inline_filters: Vec<String>,
    pub projection: String,
    pub non_key_attributes: Option<Vec<String>>,
}

#[derive(Clone, Debug)]
struct VectorIndexInfo {
    index_name: String,
    status: Option<String>,
    backfilling: Option<bool>,
    item_count: Option<i64>,
    size_bytes: Option<i64>,
    index_arn: Option<String>,
    dimensions: Option<i64>,
    distance: Option<String>,
}

fn required_string(dict: &Bound<'_, PyDict>, field: &str) -> PyResult<String> {
    dict.get_item(field)?
        .ok_or_else(|| ValidationException::new_err(format!("Vector index missing '{}'", field)))?
        .extract()
}

fn required_i64(dict: &Bound<'_, PyDict>, field: &str) -> PyResult<i64> {
    dict.get_item(field)?
        .ok_or_else(|| ValidationException::new_err(format!("Vector index missing '{}'", field)))?
        .extract()
}

pub fn parse_vector_index_definition(
    definition: &Bound<'_, PyDict>,
) -> PyResult<VectorIndexDefinition> {
    let index_name = required_string(definition, "index_name")?;
    let vector_attribute = required_string(definition, "vector_attribute")?;
    if index_name.is_empty() {
        return Err(ValidationException::new_err(
            "Vector index name cannot be empty",
        ));
    }
    if vector_attribute.is_empty() {
        return Err(ValidationException::new_err(
            "Vector attribute name cannot be empty",
        ));
    }
    let dimensions = required_i64(definition, "dimensions")?;
    if !(1..=4096).contains(&dimensions) {
        return Err(ValidationException::new_err(
            "Vector index dimensions must be between 1 and 4096",
        ));
    }

    let distance_function = required_string(definition, "distance_function")?;
    VectorDistanceFunction::try_parse(&distance_function).map_err(|_| {
        ValidationException::new_err(format!(
            "Invalid vector distance function '{}'",
            distance_function
        ))
    })?;

    let partition_key = definition
        .get_item("partition_key")?
        .map(|value| value.extract())
        .transpose()?;
    let inline_filters: Vec<String> = definition
        .get_item("inline_filters")?
        .map(|value| value.extract())
        .transpose()?
        .unwrap_or_default();
    if inline_filters.len() > 18 {
        return Err(ValidationException::new_err(
            "Vector indexes support at most 18 inline filters",
        ));
    }
    let unique_filters = inline_filters
        .iter()
        .collect::<std::collections::HashSet<_>>();
    if unique_filters.len() != inline_filters.len() {
        return Err(ValidationException::new_err(
            "Vector index contains duplicate inline filters",
        ));
    }
    if partition_key.as_ref() == Some(&vector_attribute) {
        return Err(ValidationException::new_err(
            "Vector attribute cannot also be the vector partition key",
        ));
    }
    if inline_filters.contains(&vector_attribute) {
        return Err(ValidationException::new_err(
            "Vector attribute cannot also be an inline filter",
        ));
    }
    if partition_key
        .as_ref()
        .is_some_and(|key| inline_filters.contains(key))
    {
        return Err(ValidationException::new_err(
            "Vector partition key cannot also be an inline filter",
        ));
    }

    let projection = definition
        .get_item("projection")?
        .map(|value| value.extract())
        .transpose()?
        .unwrap_or_else(|| "ALL".to_string());
    let non_key_attributes = definition
        .get_item("non_key_attributes")?
        .map(|value| value.extract())
        .transpose()?;

    Ok(VectorIndexDefinition {
        index_name,
        vector_attribute,
        dimensions,
        distance_function,
        partition_key,
        inline_filters,
        projection,
        non_key_attributes,
    })
}

pub fn parse_vector_index_definitions(
    definitions: &Bound<'_, PyList>,
) -> PyResult<Vec<VectorIndexDefinition>> {
    definitions
        .iter()
        .map(|item| parse_vector_index_definition(item.cast::<PyDict>()?))
        .collect()
}

fn build_projection(definition: &VectorIndexDefinition) -> PyResult<Projection> {
    match definition.projection.as_str() {
        "ALL" => Ok(Projection::builder()
            .projection_type(ProjectionType::All)
            .build()),
        "KEYS_ONLY" => Ok(Projection::builder()
            .projection_type(ProjectionType::KeysOnly)
            .build()),
        "INCLUDE" => {
            let attributes = definition.non_key_attributes.clone().ok_or_else(|| {
                ValidationException::new_err(
                    "non_key_attributes required when vector projection is 'INCLUDE'",
                )
            })?;
            if attributes.is_empty() {
                return Err(ValidationException::new_err(
                    "non_key_attributes cannot be empty for vector projection 'INCLUDE'",
                ));
            }
            Ok(Projection::builder()
                .projection_type(ProjectionType::Include)
                .set_non_key_attributes(Some(attributes))
                .build())
        }
        value => Err(ValidationException::new_err(format!(
            "Invalid vector projection '{}'",
            value
        ))),
    }
}

fn build_search_schema(definition: &VectorIndexDefinition) -> PyResult<Vec<SearchSchemaElement>> {
    let mut schema = Vec::new();
    if let Some(partition_key) = &definition.partition_key {
        schema.push(
            SearchSchemaElement::builder()
                .attribute_name(partition_key)
                .search_schema_element_type(SearchSchemaElementType::Hash)
                .build()
                .map_err(|error| {
                    ValidationException::new_err(format!("Invalid vector partition key: {}", error))
                })?,
        );
    }
    for filter in &definition.inline_filters {
        schema.push(
            SearchSchemaElement::builder()
                .attribute_name(filter)
                .search_schema_element_type(SearchSchemaElementType::InlineFilter)
                .build()
                .map_err(|error| {
                    ValidationException::new_err(format!("Invalid vector inline filter: {}", error))
                })?,
        );
    }
    Ok(schema)
}

fn build_vector_attribute(
    definition: &VectorIndexDefinition,
) -> PyResult<VectorAttributeDefinition> {
    VectorAttributeDefinition::builder()
        .attribute_name(&definition.vector_attribute)
        .build()
        .map_err(|error| {
            ValidationException::new_err(format!("Invalid vector attribute: {}", error))
        })
}

pub fn build_vector_index(definition: &VectorIndexDefinition) -> PyResult<VectorIndex> {
    VectorIndex::builder()
        .index_name(&definition.index_name)
        .vector_attribute(build_vector_attribute(definition)?)
        .set_search_schema(Some(build_search_schema(definition)?))
        .projection(build_projection(definition)?)
        .dimensions(definition.dimensions)
        .distance_function(VectorDistanceFunction::from(
            definition.distance_function.as_str(),
        ))
        .build()
        .map_err(|error| ValidationException::new_err(format!("Invalid vector index: {}", error)))
}

fn build_create_action(definition: &VectorIndexDefinition) -> PyResult<CreateVectorIndexAction> {
    CreateVectorIndexAction::builder()
        .index_name(&definition.index_name)
        .vector_attribute(build_vector_attribute(definition)?)
        .set_search_schema(Some(build_search_schema(definition)?))
        .projection(build_projection(definition)?)
        .dimensions(definition.dimensions)
        .distance_function(VectorDistanceFunction::from(
            definition.distance_function.as_str(),
        ))
        .build()
        .map_err(|error| ValidationException::new_err(format!("Invalid vector index: {}", error)))
}

fn info_from_description(description: &VectorIndexDescription) -> VectorIndexInfo {
    VectorIndexInfo {
        index_name: description.index_name().unwrap_or_default().to_string(),
        status: description
            .index_status()
            .map(|status| status.as_str().to_string()),
        backfilling: description.backfilling(),
        item_count: description.item_count(),
        size_bytes: description.index_size_bytes(),
        index_arn: description.index_arn().map(str::to_string),
        dimensions: description.dimensions(),
        distance: description
            .distance_function()
            .map(|distance| distance.as_str().to_string()),
    }
}

async fn execute_describe_vector_index(
    client: &Client,
    table: &str,
    index_name: &str,
) -> PyResult<Option<VectorIndexInfo>> {
    let response = client
        .describe_table()
        .table_name(table)
        .send()
        .await
        .map_err(|error| map_sdk_error(error, Some(table)))?;
    Ok(response.table().and_then(|description| {
        description
            .vector_indexes()
            .iter()
            .find(|index| index.index_name() == Some(index_name))
            .map(info_from_description)
    }))
}

pub(crate) async fn wait_for_vector_index(
    client: &Client,
    table: &str,
    index_name: &str,
    present: bool,
) -> PyResult<()> {
    let start = Instant::now();
    loop {
        if start.elapsed() > Duration::from_secs(900) {
            return Err(PyErr::new::<pyo3::exceptions::PyTimeoutError, _>(format!(
                "Timeout waiting for vector index '{}'",
                index_name
            )));
        }

        let info = execute_describe_vector_index(client, table, index_name).await?;
        if present {
            if info.as_ref().is_some_and(|value| {
                value.status.as_deref() == Some("ACTIVE") && value.backfilling != Some(true)
            }) {
                return Ok(());
            }
        } else if info.is_none() {
            return Ok(());
        }

        tokio::time::sleep(Duration::from_secs(2)).await;
    }
}

async fn execute_create_vector_index(
    client: Client,
    table: String,
    definition: VectorIndexDefinition,
    wait: bool,
) -> PyResult<()> {
    let index_name = definition.index_name.clone();
    let update = VectorIndexUpdate::builder()
        .create(build_create_action(&definition)?)
        .build();
    client
        .update_table()
        .table_name(&table)
        .vector_index_updates(update)
        .send()
        .await
        .map_err(|error| map_sdk_error(error, Some(&table)))?;
    if wait {
        wait_for_vector_index(&client, &table, &index_name, true).await?;
    }
    Ok(())
}

async fn execute_delete_vector_index(
    client: Client,
    table: String,
    index_name: String,
    wait: bool,
) -> PyResult<()> {
    let action = DeleteVectorIndexAction::builder()
        .index_name(&index_name)
        .build()
        .map_err(|error| {
            ValidationException::new_err(format!("Invalid vector index: {}", error))
        })?;
    let update = VectorIndexUpdate::builder().delete(action).build();
    client
        .update_table()
        .table_name(&table)
        .vector_index_updates(update)
        .send()
        .await
        .map_err(|error| map_sdk_error(error, Some(&table)))?;
    if wait {
        wait_for_vector_index(&client, &table, &index_name, false).await?;
    }
    Ok(())
}

fn info_to_python(py: Python<'_>, info: VectorIndexInfo) -> PyResult<Py<PyAny>> {
    let value = PyDict::new(py);
    value.set_item("index_name", info.index_name)?;
    value.set_item("status", info.status)?;
    value.set_item("backfilling", info.backfilling)?;
    value.set_item("item_count", info.item_count)?;
    value.set_item("size_bytes", info.size_bytes)?;
    value.set_item("index_arn", info.index_arn)?;
    value.set_item("dimensions", info.dimensions)?;
    value.set_item("distance", info.distance)?;
    Ok(value.into_any().unbind())
}

pub fn create_vector_index<'py>(
    py: Python<'py>,
    client: Client,
    table: &str,
    definition: &Bound<'_, PyDict>,
    wait: bool,
) -> PyResult<Bound<'py, PyAny>> {
    let definition = parse_vector_index_definition(definition)?;
    let table = table.to_string();
    pyo3_async_runtimes::tokio::future_into_py(py, async move {
        execute_create_vector_index(client, table, definition, wait).await
    })
}

pub fn sync_create_vector_index(
    py: Python<'_>,
    client: &Client,
    runtime: &Arc<Runtime>,
    table: &str,
    definition: &Bound<'_, PyDict>,
    wait: bool,
) -> PyResult<()> {
    let definition = parse_vector_index_definition(definition)?;
    let table = table.to_string();
    let client = client.clone();
    py.detach(|| runtime.block_on(execute_create_vector_index(client, table, definition, wait)))
}

pub fn delete_vector_index<'py>(
    py: Python<'py>,
    client: Client,
    table: &str,
    index_name: &str,
    wait: bool,
) -> PyResult<Bound<'py, PyAny>> {
    let table = table.to_string();
    let index_name = index_name.to_string();
    pyo3_async_runtimes::tokio::future_into_py(py, async move {
        execute_delete_vector_index(client, table, index_name, wait).await
    })
}

pub fn sync_delete_vector_index(
    py: Python<'_>,
    client: &Client,
    runtime: &Arc<Runtime>,
    table: &str,
    index_name: &str,
    wait: bool,
) -> PyResult<()> {
    let client = client.clone();
    let table = table.to_string();
    let index_name = index_name.to_string();
    py.detach(|| runtime.block_on(execute_delete_vector_index(client, table, index_name, wait)))
}

pub fn describe_vector_index<'py>(
    py: Python<'py>,
    client: Client,
    table: &str,
    index_name: &str,
) -> PyResult<Bound<'py, PyAny>> {
    let table = table.to_string();
    let index_name = index_name.to_string();
    pyo3_async_runtimes::tokio::future_into_py(py, async move {
        let info = execute_describe_vector_index(&client, &table, &index_name)
            .await?
            .ok_or_else(|| {
                ValidationException::new_err(format!(
                    "Vector index '{}' not found on table '{}'",
                    index_name, table
                ))
            })?;
        Python::attach(|py| info_to_python(py, info))
    })
}

pub fn sync_describe_vector_index(
    py: Python<'_>,
    client: &Client,
    runtime: &Arc<Runtime>,
    table: &str,
    index_name: &str,
) -> PyResult<Py<PyAny>> {
    let info =
        py.detach(|| runtime.block_on(execute_describe_vector_index(client, table, index_name)))?;
    let info = info.ok_or_else(|| {
        ValidationException::new_err(format!(
            "Vector index '{}' not found on table '{}'",
            index_name, table
        ))
    })?;
    info_to_python(py, info)
}
