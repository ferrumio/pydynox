use pyo3::prelude::*;
use pyo3::types::PyDict;

use super::DynamoDBClient;
use crate::basic_operations;
use crate::metrics::OperationMetrics;

#[pymethods]
impl DynamoDBClient {
    /// Query a single page of items from a DynamoDB table. Returns a Python awaitable.
    ///
    /// # Arguments
    ///
    /// * `table` - Table name
    /// * `key_condition_expression` - Key condition expression
    /// * `filter_expression` - Optional filter expression
    /// * `projection_expression` - Optional projection expression (saves RCU)
    /// * `expression_attribute_names` - Attribute name placeholders
    /// * `expression_attribute_values` - Attribute value placeholders
    /// * `limit` - Max items per page
    /// * `exclusive_start_key` - Start key for pagination
    /// * `scan_index_forward` - Sort order (true = ascending)
    /// * `index_name` - GSI or LSI name
    /// * `consistent_read` - Use strongly consistent read
    #[pyo3(signature = (table, key_condition_expression, filter_expression=None, projection_expression=None, expression_attribute_names=None, expression_attribute_values=None, limit=None, exclusive_start_key=None, scan_index_forward=None, index_name=None, consistent_read=false))]
    #[allow(clippy::too_many_arguments)]
    #[allow(clippy::type_complexity)]
    pub fn query_page<'py>(
        &self,
        py: Python<'py>,
        table: &str,
        key_condition_expression: &str,
        filter_expression: Option<String>,
        projection_expression: Option<String>,
        expression_attribute_names: Option<&Bound<'_, PyDict>>,
        expression_attribute_values: Option<&Bound<'_, PyDict>>,
        limit: Option<i32>,
        exclusive_start_key: Option<&Bound<'_, PyDict>>,
        scan_index_forward: Option<bool>,
        index_name: Option<String>,
        consistent_read: bool,
    ) -> PyResult<Bound<'py, PyAny>> {
        basic_operations::query(
            py,
            self.client.clone(),
            table,
            key_condition_expression,
            filter_expression,
            projection_expression,
            expression_attribute_names,
            expression_attribute_values,
            limit,
            exclusive_start_key,
            scan_index_forward,
            index_name,
            consistent_read,
        )
    }

    /// Sync query_page - blocks until complete.
    #[pyo3(signature = (table, key_condition_expression, filter_expression=None, projection_expression=None, expression_attribute_names=None, expression_attribute_values=None, limit=None, exclusive_start_key=None, scan_index_forward=None, index_name=None, consistent_read=false))]
    #[allow(clippy::too_many_arguments)]
    #[allow(clippy::type_complexity)]
    pub fn sync_query_page(
        &self,
        py: Python<'_>,
        table: &str,
        key_condition_expression: &str,
        filter_expression: Option<String>,
        projection_expression: Option<String>,
        expression_attribute_names: Option<&Bound<'_, PyDict>>,
        expression_attribute_values: Option<&Bound<'_, PyDict>>,
        limit: Option<i32>,
        exclusive_start_key: Option<&Bound<'_, PyDict>>,
        scan_index_forward: Option<bool>,
        index_name: Option<String>,
        consistent_read: bool,
    ) -> PyResult<(Vec<Py<PyAny>>, Option<Py<PyAny>>, OperationMetrics)> {
        let result = basic_operations::sync_query(
            py,
            &self.client,
            &self.runtime,
            table,
            key_condition_expression,
            filter_expression,
            projection_expression,
            expression_attribute_names,
            expression_attribute_values,
            limit,
            exclusive_start_key,
            scan_index_forward,
            index_name,
            consistent_read,
        )?;
        Ok((result.items, result.last_evaluated_key, result.metrics))
    }

    /// Scan a single page of items from a DynamoDB table. Returns a Python awaitable.
    ///
    /// # Arguments
    ///
    /// * `table` - Table name
    /// * `filter_expression` - Optional filter expression
    /// * `projection_expression` - Optional projection expression (saves RCU)
    /// * `expression_attribute_names` - Attribute name placeholders
    /// * `expression_attribute_values` - Attribute value placeholders
    /// * `limit` - Max items per page
    /// * `exclusive_start_key` - Start key for pagination
    /// * `index_name` - GSI or LSI name
    /// * `consistent_read` - Use strongly consistent read
    /// * `segment` - Segment number for parallel scan
    /// * `total_segments` - Total segments for parallel scan
    #[pyo3(signature = (table, filter_expression=None, projection_expression=None, expression_attribute_names=None, expression_attribute_values=None, limit=None, exclusive_start_key=None, index_name=None, consistent_read=false, segment=None, total_segments=None))]
    #[allow(clippy::too_many_arguments)]
    #[allow(clippy::type_complexity)]
    pub fn scan_page<'py>(
        &self,
        py: Python<'py>,
        table: &str,
        filter_expression: Option<String>,
        projection_expression: Option<String>,
        expression_attribute_names: Option<&Bound<'_, PyDict>>,
        expression_attribute_values: Option<&Bound<'_, PyDict>>,
        limit: Option<i32>,
        exclusive_start_key: Option<&Bound<'_, PyDict>>,
        index_name: Option<String>,
        consistent_read: bool,
        segment: Option<i32>,
        total_segments: Option<i32>,
    ) -> PyResult<Bound<'py, PyAny>> {
        basic_operations::scan(
            py,
            self.client.clone(),
            table,
            filter_expression,
            projection_expression,
            expression_attribute_names,
            expression_attribute_values,
            limit,
            exclusive_start_key,
            index_name,
            consistent_read,
            segment,
            total_segments,
        )
    }

    /// Sync scan_page - blocks until complete.
    #[pyo3(signature = (table, filter_expression=None, projection_expression=None, expression_attribute_names=None, expression_attribute_values=None, limit=None, exclusive_start_key=None, index_name=None, consistent_read=false, segment=None, total_segments=None))]
    #[allow(clippy::too_many_arguments)]
    #[allow(clippy::type_complexity)]
    pub fn sync_scan_page(
        &self,
        py: Python<'_>,
        table: &str,
        filter_expression: Option<String>,
        projection_expression: Option<String>,
        expression_attribute_names: Option<&Bound<'_, PyDict>>,
        expression_attribute_values: Option<&Bound<'_, PyDict>>,
        limit: Option<i32>,
        exclusive_start_key: Option<&Bound<'_, PyDict>>,
        index_name: Option<String>,
        consistent_read: bool,
        segment: Option<i32>,
        total_segments: Option<i32>,
    ) -> PyResult<(Vec<Py<PyAny>>, Option<Py<PyAny>>, OperationMetrics)> {
        let result = basic_operations::sync_scan(
            py,
            &self.client,
            &self.runtime,
            table,
            filter_expression,
            projection_expression,
            expression_attribute_names,
            expression_attribute_values,
            limit,
            exclusive_start_key,
            index_name,
            consistent_read,
            segment,
            total_segments,
        )?;
        Ok((result.items, result.last_evaluated_key, result.metrics))
    }

    /// Count items in a DynamoDB table. Returns a Python awaitable.
    #[pyo3(signature = (table, filter_expression=None, expression_attribute_names=None, expression_attribute_values=None, index_name=None, consistent_read=false))]
    #[allow(clippy::too_many_arguments)]
    pub fn count<'py>(
        &self,
        py: Python<'py>,
        table: &str,
        filter_expression: Option<String>,
        expression_attribute_names: Option<&Bound<'_, PyDict>>,
        expression_attribute_values: Option<&Bound<'_, PyDict>>,
        index_name: Option<String>,
        consistent_read: bool,
    ) -> PyResult<Bound<'py, PyAny>> {
        basic_operations::count(
            py,
            self.client.clone(),
            table,
            filter_expression,
            expression_attribute_names,
            expression_attribute_values,
            index_name,
            consistent_read,
        )
    }

    /// Sync count - blocks until complete.
    #[pyo3(signature = (table, filter_expression=None, expression_attribute_names=None, expression_attribute_values=None, index_name=None, consistent_read=false))]
    #[allow(clippy::too_many_arguments)]
    pub fn sync_count(
        &self,
        py: Python<'_>,
        table: &str,
        filter_expression: Option<String>,
        expression_attribute_names: Option<&Bound<'_, PyDict>>,
        expression_attribute_values: Option<&Bound<'_, PyDict>>,
        index_name: Option<String>,
        consistent_read: bool,
    ) -> PyResult<(i64, OperationMetrics)> {
        basic_operations::sync_count(
            py,
            &self.client,
            &self.runtime,
            table,
            filter_expression,
            expression_attribute_names,
            expression_attribute_values,
            index_name,
            consistent_read,
        )
    }

    /// Parallel scan - runs multiple segment scans concurrently. Returns a Python awaitable.
    ///
    /// This is much faster than regular scan for large tables.
    /// Each segment is scanned in parallel using tokio tasks.
    ///
    /// # Arguments
    ///
    /// * `table` - Table name
    /// * `total_segments` - Number of parallel segments (1-1000000)
    /// * `filter_expression` - Optional filter expression
    /// * `projection_expression` - Optional projection expression (saves RCU)
    /// * `expression_attribute_names` - Attribute name placeholders
    /// * `expression_attribute_values` - Attribute value placeholders
    /// * `consistent_read` - Use strongly consistent reads
    ///
    /// # Returns
    ///
    /// A Python awaitable that resolves to dict with items and metrics.
    #[pyo3(signature = (table, total_segments, filter_expression=None, projection_expression=None, expression_attribute_names=None, expression_attribute_values=None, consistent_read=false))]
    #[allow(clippy::too_many_arguments)]
    pub fn parallel_scan<'py>(
        &self,
        py: Python<'py>,
        table: &str,
        total_segments: i32,
        filter_expression: Option<String>,
        projection_expression: Option<String>,
        expression_attribute_names: Option<&Bound<'_, PyDict>>,
        expression_attribute_values: Option<&Bound<'_, PyDict>>,
        consistent_read: bool,
    ) -> PyResult<Bound<'py, PyAny>> {
        basic_operations::parallel_scan(
            py,
            self.client.clone(),
            table,
            total_segments,
            filter_expression,
            projection_expression,
            expression_attribute_names,
            expression_attribute_values,
            consistent_read,
        )
    }

    /// Sync parallel_scan - blocks until all segments complete.
    #[pyo3(signature = (table, total_segments, filter_expression=None, projection_expression=None, expression_attribute_names=None, expression_attribute_values=None, consistent_read=false))]
    #[allow(clippy::too_many_arguments)]
    pub fn sync_parallel_scan(
        &self,
        py: Python<'_>,
        table: &str,
        total_segments: i32,
        filter_expression: Option<String>,
        projection_expression: Option<String>,
        expression_attribute_names: Option<&Bound<'_, PyDict>>,
        expression_attribute_values: Option<&Bound<'_, PyDict>>,
        consistent_read: bool,
    ) -> PyResult<(Vec<Py<PyAny>>, OperationMetrics)> {
        basic_operations::sync_parallel_scan(
            py,
            &self.client,
            &self.runtime,
            table,
            total_segments,
            filter_expression,
            projection_expression,
            expression_attribute_names,
            expression_attribute_values,
            consistent_read,
        )
    }
}
