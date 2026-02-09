//! PartiQL operations.

use aws_sdk_dynamodb::types::{AttributeValue, ReturnConsumedCapacity};
use aws_sdk_dynamodb::Client;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use std::collections::HashMap;
use std::sync::Arc;
use std::time::Instant;
use tokio::runtime::Runtime;

use crate::conversions::{attribute_values_to_py_dict, py_to_attribute_value};
use crate::errors::map_sdk_error;
use crate::metrics::OperationMetrics;

/// Raw result from execute_statement (before Python conversion).
pub struct RawStatementResult {
    pub items: Vec<HashMap<String, AttributeValue>>,
    pub next_token: Option<String>,
    pub metrics: OperationMetrics,
}

/// Core async execute_statement operation.
pub async fn execute_statement_core(
    client: Client,
    statement: String,
    parameters: Option<Vec<AttributeValue>>,
    consistent_read: bool,
    next_token: Option<String>,
) -> Result<
    RawStatementResult,
    (
        aws_sdk_dynamodb::error::SdkError<
            aws_sdk_dynamodb::operation::execute_statement::ExecuteStatementError,
        >,
        String,
    ),
> {
    let mut request = client
        .execute_statement()
        .statement(&statement)
        .consistent_read(consistent_read)
        .return_consumed_capacity(ReturnConsumedCapacity::Total);

    if let Some(params) = parameters {
        request = request.set_parameters(Some(params));
    }

    if let Some(token) = next_token {
        request = request.next_token(token);
    }

    let start = Instant::now();
    let result = request.send().await;
    let duration_ms = start.elapsed().as_secs_f64() * 1000.0;

    match result {
        Ok(output) => {
            let consumed = output.consumed_capacity();
            let rcu = consumed.and_then(|c| c.read_capacity_units());
            let wcu = consumed.and_then(|c| c.write_capacity_units());

            let items = output.items.unwrap_or_default();
            let next_token = output.next_token;

            let metrics = OperationMetrics::with_capacity(duration_ms, rcu, wcu, None)
                .with_items_count(items.len());

            Ok(RawStatementResult {
                items,
                next_token,
                metrics,
            })
        }
        Err(e) => Err((e, statement)),
    }
}

/// Convert Python parameters list to AttributeValue vec.
fn convert_parameters(py: Python<'_>, params: &Bound<'_, PyList>) -> PyResult<Vec<AttributeValue>> {
    let mut result = Vec::with_capacity(params.len());
    for item in params.iter() {
        result.push(py_to_attribute_value(py, &item)?);
    }
    Ok(result)
}

/// Sync execute_statement - blocks until complete.
#[allow(clippy::too_many_arguments)]
pub fn sync_execute_statement(
    py: Python<'_>,
    client: &Client,
    runtime: &Arc<Runtime>,
    statement: &str,
    parameters: Option<&Bound<'_, PyList>>,
    consistent_read: bool,
    next_token: Option<String>,
) -> PyResult<(Vec<Py<PyAny>>, Option<String>, OperationMetrics)> {
    let params = match parameters {
        Some(list) => Some(convert_parameters(py, list)?),
        None => None,
    };

    let result = py.detach(|| {
        runtime.block_on(execute_statement_core(
            client.clone(),
            statement.to_string(),
            params,
            consistent_read,
            next_token,
        ))
    });

    match result {
        Ok(raw) => {
            let mut items = Vec::with_capacity(raw.items.len());
            for item in raw.items {
                let py_dict = attribute_values_to_py_dict(py, item)?;
                items.push(py_dict.into_any().unbind());
            }
            Ok((items, raw.next_token, raw.metrics))
        }
        Err((e, stmt)) => Err(map_sdk_error(e, Some(&stmt))),
    }
}

/// Async execute_statement - returns a Python awaitable (default).
#[allow(clippy::too_many_arguments)]
pub fn execute_statement<'py>(
    py: Python<'py>,
    client: Client,
    statement: String,
    parameters: Option<&Bound<'_, PyList>>,
    consistent_read: bool,
    next_token: Option<String>,
) -> PyResult<Bound<'py, PyAny>> {
    let params = match parameters {
        Some(list) => Some(convert_parameters(py, list)?),
        None => None,
    };

    pyo3_async_runtimes::tokio::future_into_py(py, async move {
        let result =
            execute_statement_core(client, statement, params, consistent_read, next_token).await;

        Python::attach(|py| match result {
            Ok(raw) => {
                let py_result = PyDict::new(py);

                let mut items = Vec::with_capacity(raw.items.len());
                for item in raw.items {
                    let py_dict = attribute_values_to_py_dict(py, item)?;
                    items.push(py_dict.into_any().unbind());
                }
                py_result.set_item("items", items)?;
                py_result.set_item("next_token", raw.next_token)?;
                py_result.set_item("metrics", raw.metrics.into_pyobject(py)?)?;

                Ok(py_result.into_any().unbind())
            }
            Err((e, stmt)) => Err(map_sdk_error(e, Some(&stmt))),
        })
    })
}
