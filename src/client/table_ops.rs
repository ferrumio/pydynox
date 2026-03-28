use pyo3::prelude::*;

use super::DynamoDBClient;
use crate::table_operations;

#[pymethods]
impl DynamoDBClient {
    /// Sync version of create_table. Blocks until complete.
    #[pyo3(signature = (table_name, hash_key, range_key=None, billing_mode="PAY_PER_REQUEST", read_capacity=None, write_capacity=None, table_class=None, encryption=None, kms_key_id=None, global_secondary_indexes=None, local_secondary_indexes=None, wait=false))]
    #[allow(clippy::too_many_arguments)]
    pub fn sync_create_table(
        &self,
        py: Python<'_>,
        table_name: &str,
        hash_key: (&str, &str),
        range_key: Option<(&str, &str)>,
        billing_mode: &str,
        read_capacity: Option<i64>,
        write_capacity: Option<i64>,
        table_class: Option<&str>,
        encryption: Option<&str>,
        kms_key_id: Option<&str>,
        global_secondary_indexes: Option<&Bound<'_, pyo3::types::PyList>>,
        local_secondary_indexes: Option<&Bound<'_, pyo3::types::PyList>>,
        wait: bool,
    ) -> PyResult<()> {
        let (range_key_name, range_key_type) = match range_key {
            Some((name, typ)) => (Some(name), Some(typ)),
            None => (None, None),
        };

        let gsis = match global_secondary_indexes {
            Some(list) => Some(table_operations::parse_gsi_definitions(py, list)?),
            None => None,
        };

        let lsis = match local_secondary_indexes {
            Some(list) => Some(table_operations::parse_lsi_definitions(py, list)?),
            None => None,
        };

        table_operations::sync_create_table(
            &self.client,
            &self.runtime,
            table_name,
            hash_key.0,
            hash_key.1,
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
        )
    }

    /// Sync version of table_exists. Blocks until complete.
    pub fn sync_table_exists(&self, table_name: &str) -> PyResult<bool> {
        table_operations::sync_table_exists(&self.client, &self.runtime, table_name)
    }

    /// Sync version of delete_table. Blocks until complete.
    pub fn sync_delete_table(&self, table_name: &str) -> PyResult<()> {
        table_operations::sync_delete_table(&self.client, &self.runtime, table_name)
    }

    /// Sync version of wait_for_table_active. Blocks until complete.
    #[pyo3(signature = (table_name, timeout_seconds=None))]
    pub fn sync_wait_for_table_active(
        &self,
        table_name: &str,
        timeout_seconds: Option<u64>,
    ) -> PyResult<()> {
        table_operations::sync_wait_for_table_active(
            &self.client,
            &self.runtime,
            table_name,
            timeout_seconds,
        )
    }

    /// Create a new DynamoDB table. Returns a Python awaitable.
    #[pyo3(signature = (table_name, hash_key, range_key=None, billing_mode="PAY_PER_REQUEST", read_capacity=None, write_capacity=None, table_class=None, encryption=None, kms_key_id=None, global_secondary_indexes=None, local_secondary_indexes=None, wait=false))]
    #[allow(clippy::too_many_arguments)]
    pub fn create_table<'py>(
        &self,
        py: Python<'py>,
        table_name: &str,
        hash_key: (&str, &str),
        range_key: Option<(&str, &str)>,
        billing_mode: &str,
        read_capacity: Option<i64>,
        write_capacity: Option<i64>,
        table_class: Option<&str>,
        encryption: Option<&str>,
        kms_key_id: Option<&str>,
        global_secondary_indexes: Option<&Bound<'_, pyo3::types::PyList>>,
        local_secondary_indexes: Option<&Bound<'_, pyo3::types::PyList>>,
        wait: bool,
    ) -> PyResult<Bound<'py, PyAny>> {
        let (range_key_name, range_key_type) = match range_key {
            Some((name, typ)) => (Some(name), Some(typ)),
            None => (None, None),
        };

        let gsis = match global_secondary_indexes {
            Some(list) => Some(table_operations::parse_gsi_definitions(py, list)?),
            None => None,
        };

        let lsis = match local_secondary_indexes {
            Some(list) => Some(table_operations::parse_lsi_definitions(py, list)?),
            None => None,
        };

        table_operations::create_table(
            py,
            self.client.clone(),
            table_name,
            hash_key.0,
            hash_key.1,
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
        )
    }

    /// Check if a table exists. Returns a Python awaitable.
    pub fn table_exists<'py>(
        &self,
        py: Python<'py>,
        table_name: &str,
    ) -> PyResult<Bound<'py, PyAny>> {
        table_operations::table_exists(py, self.client.clone(), table_name)
    }

    /// Delete a table. Returns a Python awaitable.
    pub fn delete_table<'py>(
        &self,
        py: Python<'py>,
        table_name: &str,
    ) -> PyResult<Bound<'py, PyAny>> {
        table_operations::delete_table(py, self.client.clone(), table_name)
    }

    /// Wait for a table to become active. Returns a Python awaitable.
    #[pyo3(signature = (table_name, timeout_seconds=None))]
    pub fn wait_for_table_active<'py>(
        &self,
        py: Python<'py>,
        table_name: &str,
        timeout_seconds: Option<u64>,
    ) -> PyResult<Bound<'py, PyAny>> {
        table_operations::wait_for_table_active(
            py,
            self.client.clone(),
            table_name,
            timeout_seconds,
        )
    }
}
