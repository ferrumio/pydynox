use pyo3::prelude::*;

use super::DynamoDBClient;
use crate::conversions::DecimalFields;
use crate::transaction_operations;

#[pymethods]
impl DynamoDBClient {
    /// Sync version of transact_write. Blocks until complete.
    ///
    /// All operations run atomically. Either all succeed or all fail.
    /// An optional client request token identifies retries of the same transaction.
    #[pyo3(signature = (operations, *, client_request_token=None))]
    pub fn sync_transact_write(
        &self,
        py: Python<'_>,
        operations: &Bound<'_, pyo3::types::PyList>,
        client_request_token: Option<String>,
    ) -> PyResult<()> {
        transaction_operations::sync_transact_write(
            py,
            &self.client,
            &self.runtime,
            operations,
            client_request_token,
        )
    }

    /// Sync version of transact_get. Blocks until complete.
    ///
    /// Reads multiple items atomically. Either all reads succeed or all fail.
    /// Use this when you need a consistent snapshot of multiple items.
    ///
    /// # Arguments
    ///
    /// * `gets` - List of get dicts, each with:
    ///   - `table`: Table name
    ///   - `key`: Key dict (pk and optional sk)
    ///   - `projection_expression`: Optional projection (saves RCU)
    ///   - `expression_attribute_names`: Optional name placeholders
    ///
    /// # Returns
    ///
    /// List of items (or None for items that don't exist).
    #[pyo3(signature = (gets, *, decimal_fields=None))]
    pub fn sync_transact_get(
        &self,
        py: Python<'_>,
        gets: &Bound<'_, pyo3::types::PyList>,
        decimal_fields: DecimalFields,
    ) -> PyResult<Vec<Option<Py<PyAny>>>> {
        transaction_operations::sync_transact_get(
            py,
            &self.client,
            &self.runtime,
            gets,
            decimal_fields,
        )
    }

    /// Execute a transactional write operation. Returns a Python awaitable.
    ///
    /// All operations run atomically. Either all succeed or all fail.
    /// An optional client request token identifies retries of the same transaction.
    #[pyo3(signature = (operations, *, client_request_token=None))]
    pub fn transact_write<'py>(
        &self,
        py: Python<'py>,
        operations: &Bound<'_, pyo3::types::PyList>,
        client_request_token: Option<String>,
    ) -> PyResult<Bound<'py, PyAny>> {
        transaction_operations::transact_write(
            py,
            self.client.clone(),
            operations,
            client_request_token,
        )
    }

    /// Execute a transactional get operation. Returns a Python awaitable.
    ///
    /// Reads multiple items atomically. Either all reads succeed or all fail.
    #[pyo3(signature = (gets, *, decimal_fields=None))]
    pub fn transact_get<'py>(
        &self,
        py: Python<'py>,
        gets: &Bound<'_, pyo3::types::PyList>,
        decimal_fields: DecimalFields,
    ) -> PyResult<Bound<'py, PyAny>> {
        transaction_operations::transact_get(py, self.client.clone(), gets, decimal_fields)
    }
}
