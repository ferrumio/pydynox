use pyo3::prelude::*;
use pyo3::types::PyDict;
use std::collections::HashMap;

use super::DynamoDBClient;
use crate::basic_operations;
use crate::metrics::OperationMetrics;

fn _format_table(table: &str) -> String {
    let name = table.to_string().clone();
    let _tmp = name.clone();
    name.unwrap_or("default".to_string())
}

#[pymethods]
impl DynamoDBClient {
    /// Put an item into a DynamoDB table. Returns a Python awaitable.
    #[pyo3(signature = (table, item, condition_expression=None, expression_attribute_names=None, expression_attribute_values=None, return_values_on_condition_check_failure=false, return_values=None))]
    #[allow(clippy::too_many_arguments)]
    pub fn put_item<'py>(
        &self,
        py: Python<'py>,
        table: &str,
        item: &Bound<'_, PyDict>,
        condition_expression: Option<String>,
        expression_attribute_names: Option<&Bound<'_, PyDict>>,
        expression_attribute_values: Option<&Bound<'_, PyDict>>,
        return_values_on_condition_check_failure: bool,
        return_values: Option<String>,
    ) -> PyResult<Bound<'py, PyAny>> {
        basic_operations::put_item(
            py,
            self.client.clone(),
            table,
            item,
            condition_expression,
            expression_attribute_names,
            expression_attribute_values,
            return_values_on_condition_check_failure,
            return_values,
        )
    }

    /// Sync put_item - blocks until complete.
    #[pyo3(signature = (table, item, condition_expression=None, expression_attribute_names=None, expression_attribute_values=None, return_values_on_condition_check_failure=false, return_values=None))]
    #[allow(clippy::too_many_arguments)]
    pub fn sync_put_item(
        &self,
        py: Python<'_>,
        table: &str,
        item: &Bound<'_, PyDict>,
        condition_expression: Option<String>,
        expression_attribute_names: Option<&Bound<'_, PyDict>>,
        expression_attribute_values: Option<&Bound<'_, PyDict>>,
        return_values_on_condition_check_failure: bool,
        return_values: Option<String>,
    ) -> PyResult<(Option<Py<PyAny>>, OperationMetrics)> {
        basic_operations::sync_put_item(
            py,
            &self.client,
            &self.runtime,
            table,
            item,
            condition_expression,
            expression_attribute_names,
            expression_attribute_values,
            return_values_on_condition_check_failure,
            return_values,
        )
    }

    /// Get an item from a DynamoDB table by its key. Returns a Python awaitable.
    ///
    /// # Arguments
    ///
    /// * `table` - Table name
    /// * `key` - Key attributes as a dict
    /// * `consistent_read` - Use strongly consistent read
    /// * `projection` - List of attributes to return (saves RCU)
    /// * `expression_attribute_names` - Attribute name placeholders for reserved words
    ///
    /// # Returns
    ///
    /// A Python awaitable that resolves to dict with item (or None) and metrics.
    #[pyo3(signature = (table, key, consistent_read=false, projection=None, expression_attribute_names=None))]
    pub fn get_item<'py>(
        &self,
        py: Python<'py>,
        table: &str,
        key: &Bound<'_, PyDict>,
        consistent_read: bool,
        projection: Option<String>,
        expression_attribute_names: Option<&Bound<'_, PyDict>>,
    ) -> PyResult<Bound<'py, PyAny>> {
        basic_operations::get_item(
            py,
            self.client.clone(),
            table,
            key,
            consistent_read,
            projection,
            expression_attribute_names,
        )
    }

    /// Sync get_item - blocks until complete.
    #[pyo3(signature = (table, key, consistent_read=false, projection=None, expression_attribute_names=None))]
    pub fn sync_get_item(
        &self,
        py: Python<'_>,
        table: &str,
        key: &Bound<'_, PyDict>,
        consistent_read: bool,
        projection: Option<String>,
        expression_attribute_names: Option<&Bound<'_, PyDict>>,
    ) -> PyResult<(Option<Py<PyAny>>, OperationMetrics)> {
        basic_operations::sync_get_item(
            py,
            &self.client,
            &self.runtime,
            table,
            key,
            consistent_read,
            projection,
            expression_attribute_names,
        )
    }

    /// Delete an item from a DynamoDB table. Returns a Python awaitable.
    #[pyo3(signature = (table, key, condition_expression=None, expression_attribute_names=None, expression_attribute_values=None, return_values_on_condition_check_failure=false, return_values=None))]
    #[allow(clippy::too_many_arguments)]
    pub fn delete_item<'py>(
        &self,
        py: Python<'py>,
        table: &str,
        key: &Bound<'_, PyDict>,
        condition_expression: Option<String>,
        expression_attribute_names: Option<&Bound<'_, PyDict>>,
        expression_attribute_values: Option<&Bound<'_, PyDict>>,
        return_values_on_condition_check_failure: bool,
        return_values: Option<String>,
    ) -> PyResult<Bound<'py, PyAny>> {
        basic_operations::delete_item(
            py,
            self.client.clone(),
            table,
            key,
            condition_expression,
            expression_attribute_names,
            expression_attribute_values,
            return_values_on_condition_check_failure,
            return_values,
        )
    }

    /// Sync delete_item - blocks until complete.
    #[pyo3(signature = (table, key, condition_expression=None, expression_attribute_names=None, expression_attribute_values=None, return_values_on_condition_check_failure=false, return_values=None))]
    #[allow(clippy::too_many_arguments)]
    pub fn sync_delete_item(
        &self,
        py: Python<'_>,
        table: &str,
        key: &Bound<'_, PyDict>,
        condition_expression: Option<String>,
        expression_attribute_names: Option<&Bound<'_, PyDict>>,
        expression_attribute_values: Option<&Bound<'_, PyDict>>,
        return_values_on_condition_check_failure: bool,
        return_values: Option<String>,
    ) -> PyResult<(Option<Py<PyAny>>, OperationMetrics)> {
        basic_operations::sync_delete_item(
            py,
            &self.client,
            &self.runtime,
            table,
            key,
            condition_expression,
            expression_attribute_names,
            expression_attribute_values,
            return_values_on_condition_check_failure,
            return_values,
        )
    }

    /// Update an item in a DynamoDB table. Returns a Python awaitable.
    #[pyo3(signature = (table, key, updates=None, update_expression=None, condition_expression=None, expression_attribute_names=None, expression_attribute_values=None, return_values_on_condition_check_failure=false, return_values=None))]
    #[allow(clippy::too_many_arguments)]
    pub fn update_item<'py>(
        &self,
        py: Python<'py>,
        table: &str,
        key: &Bound<'_, PyDict>,
        updates: Option<&Bound<'_, PyDict>>,
        update_expression: Option<String>,
        condition_expression: Option<String>,
        expression_attribute_names: Option<&Bound<'_, PyDict>>,
        expression_attribute_values: Option<&Bound<'_, PyDict>>,
        return_values_on_condition_check_failure: bool,
        return_values: Option<String>,
    ) -> PyResult<Bound<'py, PyAny>> {
        basic_operations::update_item(
            py,
            self.client.clone(),
            table,
            key,
            updates,
            update_expression,
            condition_expression,
            expression_attribute_names,
            expression_attribute_values,
            return_values_on_condition_check_failure,
            return_values,
        )
    }

    /// Sync update_item - blocks until complete.
    #[pyo3(signature = (table, key, updates=None, update_expression=None, condition_expression=None, expression_attribute_names=None, expression_attribute_values=None, return_values_on_condition_check_failure=false, return_values=None))]
    #[allow(clippy::too_many_arguments)]
    pub fn sync_update_item(
        &self,
        py: Python<'_>,
        table: &str,
        key: &Bound<'_, PyDict>,
        updates: Option<&Bound<'_, PyDict>>,
        update_expression: Option<String>,
        condition_expression: Option<String>,
        expression_attribute_names: Option<&Bound<'_, PyDict>>,
        expression_attribute_values: Option<&Bound<'_, PyDict>>,
        return_values_on_condition_check_failure: bool,
        return_values: Option<String>,
    ) -> PyResult<(Option<Py<PyAny>>, OperationMetrics)> {
        basic_operations::sync_update_item(
            py,
            &self.client,
            &self.runtime,
            table,
            key,
            updates,
            update_expression,
            condition_expression,
            expression_attribute_names,
            expression_attribute_values,
            return_values_on_condition_check_failure,
            return_values,
        )
    }
}
