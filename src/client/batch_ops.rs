use pyo3::prelude::*;

use super::DynamoDBClient;
use crate::batch_operations;

#[pymethods]
impl DynamoDBClient {
    /// Sync batch write items to a DynamoDB table.
    pub fn sync_batch_write(
        &self,
        py: Python<'_>,
        table: &str,
        put_items: &Bound<'_, pyo3::types::PyList>,
        delete_keys: &Bound<'_, pyo3::types::PyList>,
    ) -> PyResult<()> {
        batch_operations::sync_batch_write(
            py,
            &self.client,
            &self.runtime,
            table,
            put_items,
            delete_keys,
        )
    }

    /// Sync batch get items from a DynamoDB table.
    pub fn sync_batch_get(
        &self,
        py: Python<'_>,
        table: &str,
        keys: &Bound<'_, pyo3::types::PyList>,
        consistent_read: bool,
    ) -> PyResult<Vec<Py<PyAny>>> {
        batch_operations::sync_batch_get(
            py,
            &self.client,
            &self.runtime,
            table,
            keys,
            consistent_read,
        )
    }

    /// Async batch write items to a DynamoDB table (default, no prefix).
    ///
    /// Returns a Python awaitable that writes items in batch.
    pub fn batch_write<'py>(
        &self,
        py: Python<'py>,
        table: &str,
        put_items: &Bound<'_, pyo3::types::PyList>,
        delete_keys: &Bound<'_, pyo3::types::PyList>,
    ) -> PyResult<Bound<'py, PyAny>> {
        batch_operations::batch_write(py, self.client.clone(), table, put_items, delete_keys)
    }

    /// Async batch get items from a DynamoDB table (default, no prefix).
    ///
    /// Returns a Python awaitable that gets items in batch.
    pub fn batch_get<'py>(
        &self,
        py: Python<'py>,
        table: &str,
        keys: &Bound<'_, pyo3::types::PyList>,
        consistent_read: bool,
    ) -> PyResult<Bound<'py, PyAny>> {
        batch_operations::batch_get(py, self.client.clone(), table, keys, consistent_read)
    }
}
