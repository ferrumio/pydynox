//! SearchVectors operation.

use aws_sdk_dynamodb::Client;
use aws_sdk_dynamodb::types::{AttributeValue, ReturnConsumedCapacity};
use aws_types::request_id::RequestId;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use std::collections::HashMap;
use std::sync::Arc;
use std::time::Instant;
use tokio::runtime::Runtime;

use crate::conversions::{
    attribute_values_to_py_dict, extract_string_map, py_dict_to_attribute_values,
};
use crate::errors::map_sdk_error;
use crate::metrics::OperationMetrics;

pub struct PreparedSearchVectors {
    table: String,
    index_name: String,
    vector: Vec<AttributeValue>,
    top_k: i32,
    search_condition_expression: Option<String>,
    expression_attribute_names: Option<HashMap<String, String>>,
    expression_attribute_values: Option<HashMap<String, AttributeValue>>,
    projection_expression: Option<String>,
}

struct RawVectorMatch {
    item: HashMap<String, AttributeValue>,
    score: f64,
}

struct RawVectorSearchResult {
    matches: Vec<RawVectorMatch>,
    metrics: OperationMetrics,
}

#[allow(clippy::too_many_arguments)]
fn prepare_search_vectors(
    py: Python<'_>,
    table: &str,
    index_name: &str,
    vector: Vec<f64>,
    top_k: i32,
    search_condition_expression: Option<String>,
    expression_attribute_names: Option<&Bound<'_, PyDict>>,
    expression_attribute_values: Option<&Bound<'_, PyDict>>,
    projection_expression: Option<String>,
) -> PyResult<PreparedSearchVectors> {
    if !(1..=100).contains(&top_k) {
        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            "top_k must be between 1 and 100",
        ));
    }
    if vector.is_empty() || vector.len() > 4096 {
        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            "vector must contain between 1 and 4096 dimensions",
        ));
    }

    let mut search_vector = Vec::with_capacity(vector.len());
    for (index, value) in vector.into_iter().enumerate() {
        if !value.is_finite() {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                "vector contains a non-finite value at index {}",
                index
            )));
        }
        let value = value as f32;
        if !value.is_finite() {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                "vector contains a value outside float32 range at index {}",
                index
            )));
        }
        search_vector.push(AttributeValue::N(value.to_string()));
    }

    let names = extract_string_map(expression_attribute_names)?;
    let values = match expression_attribute_values {
        Some(dict) => Some(py_dict_to_attribute_values(py, dict)?),
        None => None,
    };

    Ok(PreparedSearchVectors {
        table: table.to_string(),
        index_name: index_name.to_string(),
        vector: search_vector,
        top_k,
        search_condition_expression,
        expression_attribute_names: names,
        expression_attribute_values: values,
        projection_expression,
    })
}

async fn execute_search_vectors(
    client: Client,
    prepared: PreparedSearchVectors,
) -> Result<
    RawVectorSearchResult,
    (
        aws_sdk_dynamodb::error::SdkError<
            aws_sdk_dynamodb::operation::search_vectors::SearchVectorsError,
        >,
        String,
    ),
> {
    let mut request = client
        .search_vectors()
        .table_name(&prepared.table)
        .index_name(prepared.index_name)
        .set_search_vector(Some(prepared.vector))
        .top_k(prepared.top_k)
        .return_consumed_capacity(ReturnConsumedCapacity::Total);

    if let Some(expression) = prepared.search_condition_expression {
        request = request.search_condition_expression(expression);
    }
    if let Some(names) = prepared.expression_attribute_names {
        request = request.set_expression_attribute_names(Some(names));
    }
    if let Some(values) = prepared.expression_attribute_values {
        request = request.set_expression_attribute_values(Some(values));
    }
    if let Some(projection) = prepared.projection_expression {
        request = request.projection_expression(projection);
    }

    let start = Instant::now();
    let result = request.send().await;
    let duration_ms = start.elapsed().as_secs_f64() * 1000.0;

    match result {
        Ok(output) => {
            let request_id = output.request_id().map(str::to_string);
            let search_bytes = output
                .consumed_capacity()
                .and_then(|capacity| capacity.vector_search_request_bytes());
            let matches = output
                .search_results
                .unwrap_or_default()
                .into_iter()
                .map(|result| RawVectorMatch {
                    item: result.item.unwrap_or_default(),
                    score: result.score,
                })
                .collect::<Vec<_>>();
            let metrics = OperationMetrics::with_capacity(duration_ms, None, None, request_id)
                .with_items_count(matches.len())
                .with_vector_capacity(search_bytes, None);

            Ok(RawVectorSearchResult { matches, metrics })
        }
        Err(error) => Err((error, prepared.table)),
    }
}

fn raw_to_python(py: Python<'_>, raw: RawVectorSearchResult) -> PyResult<Py<PyAny>> {
    let result = PyDict::new(py);
    let matches = PyList::empty(py);

    for vector_match in raw.matches {
        let value = PyDict::new(py);
        value.set_item("item", attribute_values_to_py_dict(py, vector_match.item)?)?;
        value.set_item("score", vector_match.score)?;
        matches.append(value)?;
    }

    result.set_item("matches", matches)?;
    result.set_item("metrics", raw.metrics)?;
    Ok(result.into_any().unbind())
}

#[allow(clippy::too_many_arguments)]
pub fn sync_search_vectors(
    py: Python<'_>,
    client: &Client,
    runtime: &Arc<Runtime>,
    table: &str,
    index_name: &str,
    vector: Vec<f64>,
    top_k: i32,
    search_condition_expression: Option<String>,
    expression_attribute_names: Option<&Bound<'_, PyDict>>,
    expression_attribute_values: Option<&Bound<'_, PyDict>>,
    projection_expression: Option<String>,
) -> PyResult<Py<PyAny>> {
    let prepared = prepare_search_vectors(
        py,
        table,
        index_name,
        vector,
        top_k,
        search_condition_expression,
        expression_attribute_names,
        expression_attribute_values,
        projection_expression,
    )?;
    let result = py.detach(|| runtime.block_on(execute_search_vectors(client.clone(), prepared)));

    match result {
        Ok(raw) => raw_to_python(py, raw),
        Err((error, table)) => Err(map_sdk_error(error, Some(&table))),
    }
}

#[allow(clippy::too_many_arguments)]
pub fn search_vectors<'py>(
    py: Python<'py>,
    client: Client,
    table: &str,
    index_name: &str,
    vector: Vec<f64>,
    top_k: i32,
    search_condition_expression: Option<String>,
    expression_attribute_names: Option<&Bound<'_, PyDict>>,
    expression_attribute_values: Option<&Bound<'_, PyDict>>,
    projection_expression: Option<String>,
) -> PyResult<Bound<'py, PyAny>> {
    let prepared = prepare_search_vectors(
        py,
        table,
        index_name,
        vector,
        top_k,
        search_condition_expression,
        expression_attribute_names,
        expression_attribute_values,
        projection_expression,
    )?;

    pyo3_async_runtimes::tokio::future_into_py(py, async move {
        match execute_search_vectors(client, prepared).await {
            Ok(raw) => Python::attach(|py| raw_to_python(py, raw)),
            Err((error, table)) => Err(map_sdk_error(error, Some(&table))),
        }
    })
}
