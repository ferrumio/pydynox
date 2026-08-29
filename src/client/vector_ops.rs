use pyo3::prelude::*;
use pyo3::types::PyDict;

use super::DynamoDBClient;
use crate::table_operations;
use crate::vector_operations;

#[pymethods]
impl DynamoDBClient {
    #[pyo3(signature = (table, index_name, vector, top_k=10, search_condition_expression=None, expression_attribute_names=None, expression_attribute_values=None, projection_expression=None))]
    #[allow(clippy::too_many_arguments)]
    pub fn search_vectors<'py>(
        &self,
        py: Python<'py>,
        table: &str,
        index_name: &str,
        vector: Vec<f64>,
        top_k: i32,
        search_condition_expression: Option<String>,
        expression_attribute_names: Option<&Bound<'_, PyDict>>,
        expression_attribute_values: Option<&Bound<'_, PyDict>>,
        projection_expression: Option<String>,
    ) -> PyResult<Bound<'py, PyAny>> {
        vector_operations::search_vectors(
            py,
            self.client.clone(),
            table,
            index_name,
            vector,
            top_k,
            search_condition_expression,
            expression_attribute_names,
            expression_attribute_values,
            projection_expression,
        )
    }

    #[pyo3(signature = (table, index_name, vector, top_k=10, search_condition_expression=None, expression_attribute_names=None, expression_attribute_values=None, projection_expression=None))]
    #[allow(clippy::too_many_arguments)]
    pub fn sync_search_vectors(
        &self,
        py: Python<'_>,
        table: &str,
        index_name: &str,
        vector: Vec<f64>,
        top_k: i32,
        search_condition_expression: Option<String>,
        expression_attribute_names: Option<&Bound<'_, PyDict>>,
        expression_attribute_values: Option<&Bound<'_, PyDict>>,
        projection_expression: Option<String>,
    ) -> PyResult<Py<PyAny>> {
        vector_operations::sync_search_vectors(
            py,
            &self.client,
            &self.runtime,
            table,
            index_name,
            vector,
            top_k,
            search_condition_expression,
            expression_attribute_names,
            expression_attribute_values,
            projection_expression,
        )
    }

    #[pyo3(signature = (table, definition, wait=false, timeout_seconds=None))]
    pub fn create_vector_index<'py>(
        &self,
        py: Python<'py>,
        table: &str,
        definition: &Bound<'_, PyDict>,
        wait: bool,
        timeout_seconds: Option<u64>,
    ) -> PyResult<Bound<'py, PyAny>> {
        table_operations::create_vector_index(
            py,
            self.client.clone(),
            table,
            definition,
            wait,
            timeout_seconds,
        )
    }

    #[pyo3(signature = (table, definition, wait=false, timeout_seconds=None))]
    pub fn sync_create_vector_index(
        &self,
        py: Python<'_>,
        table: &str,
        definition: &Bound<'_, PyDict>,
        wait: bool,
        timeout_seconds: Option<u64>,
    ) -> PyResult<()> {
        table_operations::sync_create_vector_index(
            py,
            &self.client,
            &self.runtime,
            table,
            definition,
            wait,
            timeout_seconds,
        )
    }

    #[pyo3(signature = (table, index_name, wait=false, timeout_seconds=None))]
    pub fn delete_vector_index<'py>(
        &self,
        py: Python<'py>,
        table: &str,
        index_name: &str,
        wait: bool,
        timeout_seconds: Option<u64>,
    ) -> PyResult<Bound<'py, PyAny>> {
        table_operations::delete_vector_index(
            py,
            self.client.clone(),
            table,
            index_name,
            wait,
            timeout_seconds,
        )
    }

    #[pyo3(signature = (table, index_name, wait=false, timeout_seconds=None))]
    pub fn sync_delete_vector_index(
        &self,
        py: Python<'_>,
        table: &str,
        index_name: &str,
        wait: bool,
        timeout_seconds: Option<u64>,
    ) -> PyResult<()> {
        table_operations::sync_delete_vector_index(
            py,
            &self.client,
            &self.runtime,
            table,
            index_name,
            wait,
            timeout_seconds,
        )
    }

    pub fn describe_vector_index<'py>(
        &self,
        py: Python<'py>,
        table: &str,
        index_name: &str,
    ) -> PyResult<Bound<'py, PyAny>> {
        table_operations::describe_vector_index(py, self.client.clone(), table, index_name)
    }

    pub fn sync_describe_vector_index(
        &self,
        py: Python<'_>,
        table: &str,
        index_name: &str,
    ) -> PyResult<Py<PyAny>> {
        table_operations::sync_describe_vector_index(
            py,
            &self.client,
            &self.runtime,
            table,
            index_name,
        )
    }
}
