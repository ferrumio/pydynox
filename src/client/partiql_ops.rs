use pyo3::prelude::*;

use super::DynamoDBClient;
use crate::basic_operations;
use crate::conversions::DecimalFields;
use crate::metrics::OperationMetrics;

#[pymethods]
impl DynamoDBClient {
    /// Execute a PartiQL statement. Returns a Python awaitable.
    #[pyo3(signature = (statement, parameters=None, consistent_read=false, next_token=None, *, decimal_fields=None))]
    pub fn execute_statement<'py>(
        &self,
        py: Python<'py>,
        statement: &str,
        parameters: Option<&Bound<'_, pyo3::types::PyList>>,
        consistent_read: bool,
        next_token: Option<String>,
        decimal_fields: DecimalFields,
    ) -> PyResult<Bound<'py, PyAny>> {
        basic_operations::execute_statement(
            py,
            self.client.clone(),
            statement.to_string(),
            parameters,
            consistent_read,
            next_token,
            decimal_fields,
        )
    }

    /// Sync execute_statement - blocks until complete.
    #[pyo3(signature = (statement, parameters=None, consistent_read=false, next_token=None, *, decimal_fields=None))]
    pub fn sync_execute_statement(
        &self,
        py: Python<'_>,
        statement: &str,
        parameters: Option<&Bound<'_, pyo3::types::PyList>>,
        consistent_read: bool,
        next_token: Option<String>,
        decimal_fields: DecimalFields,
    ) -> PyResult<(Vec<Py<PyAny>>, Option<String>, OperationMetrics)> {
        basic_operations::sync_execute_statement(
            py,
            &self.client,
            &self.runtime,
            statement,
            parameters,
            consistent_read,
            next_token,
            decimal_fields,
        )
    }
}
