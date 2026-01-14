"""Scan and count operations (sync + async)."""

from __future__ import annotations

from typing import Any

from pydynox._internal._logging import _log_operation
from pydynox._internal._metrics import OperationMetrics
from pydynox.query import AsyncScanResult, ScanResult


class ScanOperations:
    """Scan and count operations."""

    # ========== SCAN ==========

    def scan(
        self,
        table: str,
        filter_expression: str | None = None,
        projection_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
        limit: int | None = None,
        index_name: str | None = None,
        last_evaluated_key: dict[str, Any] | None = None,
        consistent_read: bool = False,
        segment: int | None = None,
        total_segments: int | None = None,
    ) -> ScanResult:
        """Scan items from a DynamoDB table.

        Args:
            table: Table name.
            filter_expression: Optional filter expression.
            projection_expression: Optional projection expression (saves RCU).
            expression_attribute_names: Attribute name placeholders.
            expression_attribute_values: Attribute value placeholders.
            limit: Max items per page.
            index_name: GSI or LSI name.
            last_evaluated_key: Start key for pagination.
            consistent_read: Use strongly consistent read.
            segment: Segment number for parallel scan.
            total_segments: Total segments for parallel scan.

        Returns:
            ScanResult iterator.
        """
        return ScanResult(
            self._client,  # type: ignore[attr-defined]
            table,
            filter_expression=filter_expression,
            projection_expression=projection_expression,
            expression_attribute_names=expression_attribute_names,
            expression_attribute_values=expression_attribute_values,
            limit=limit,
            index_name=index_name,
            last_evaluated_key=last_evaluated_key,
            acquire_rcu=self._acquire_rcu,  # type: ignore[attr-defined]
            consistent_read=consistent_read,
            segment=segment,
            total_segments=total_segments,
        )

    def async_scan(
        self,
        table: str,
        filter_expression: str | None = None,
        projection_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
        limit: int | None = None,
        index_name: str | None = None,
        last_evaluated_key: dict[str, Any] | None = None,
        consistent_read: bool = False,
        segment: int | None = None,
        total_segments: int | None = None,
    ) -> AsyncScanResult:
        """Async scan items from a DynamoDB table.

        Args:
            table: Table name.
            filter_expression: Optional filter expression.
            projection_expression: Optional projection expression (saves RCU).
            expression_attribute_names: Attribute name placeholders.
            expression_attribute_values: Attribute value placeholders.
            limit: Max items per page.
            index_name: GSI or LSI name.
            last_evaluated_key: Start key for pagination.
            consistent_read: Use strongly consistent read.
            segment: Segment number for parallel scan.
            total_segments: Total segments for parallel scan.

        Returns:
            AsyncScanResult iterator.
        """
        return AsyncScanResult(
            self._client,  # type: ignore[attr-defined]
            table,
            filter_expression=filter_expression,
            projection_expression=projection_expression,
            expression_attribute_names=expression_attribute_names,
            expression_attribute_values=expression_attribute_values,
            limit=limit,
            index_name=index_name,
            last_evaluated_key=last_evaluated_key,
            acquire_rcu=self._acquire_rcu,  # type: ignore[attr-defined]
            consistent_read=consistent_read,
            segment=segment,
            total_segments=total_segments,
        )

    # ========== COUNT ==========

    def count(
        self,
        table: str,
        filter_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
        index_name: str | None = None,
        consistent_read: bool = False,
    ) -> tuple[int, OperationMetrics]:
        """Count items in a DynamoDB table."""
        count, metrics = self._client.count(  # type: ignore[attr-defined]
            table,
            filter_expression=filter_expression,
            expression_attribute_names=expression_attribute_names,
            expression_attribute_values=expression_attribute_values,
            index_name=index_name,
            consistent_read=consistent_read,
        )
        _log_operation("count", table, metrics.duration_ms, consumed_rcu=metrics.consumed_rcu)
        return count, metrics

    async def async_count(
        self,
        table: str,
        filter_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
        index_name: str | None = None,
        consistent_read: bool = False,
    ) -> tuple[int, OperationMetrics]:
        """Async count items in a DynamoDB table."""
        result = await self._client.async_count(  # type: ignore[attr-defined]
            table,
            filter_expression=filter_expression,
            expression_attribute_names=expression_attribute_names,
            expression_attribute_values=expression_attribute_values,
            index_name=index_name,
            consistent_read=consistent_read,
        )
        count: int = result["count"]
        metrics: OperationMetrics = result["metrics"]
        _log_operation("count", table, metrics.duration_ms, consumed_rcu=metrics.consumed_rcu)
        return count, metrics

    # ========== PARALLEL SCAN ==========

    def parallel_scan(
        self,
        table: str,
        total_segments: int,
        filter_expression: str | None = None,
        projection_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
        consistent_read: bool = False,
    ) -> tuple[list[dict[str, Any]], OperationMetrics]:
        """Parallel scan - runs multiple segment scans concurrently.

        Much faster than regular scan for large tables. Each segment is
        scanned in parallel using tokio tasks in Rust.

        Args:
            table: Table name.
            total_segments: Number of parallel segments (1-1000000).
            filter_expression: Optional filter expression.
            projection_expression: Optional projection expression (saves RCU).
            expression_attribute_names: Attribute name placeholders.
            expression_attribute_values: Attribute value placeholders.
            consistent_read: Use strongly consistent reads.

        Returns:
            Tuple of (items, metrics) where items is a list of all scanned items.

        Example:
            >>> items, metrics = client.parallel_scan("users", total_segments=4)
            >>> print(f"Found {len(items)} items in {metrics.duration_ms:.2f}ms")
        """
        items, metrics = self._client.parallel_scan(  # type: ignore[attr-defined]
            table,
            total_segments,
            filter_expression=filter_expression,
            projection_expression=projection_expression,
            expression_attribute_names=expression_attribute_names,
            expression_attribute_values=expression_attribute_values,
            consistent_read=consistent_read,
        )
        _log_operation(
            "parallel_scan", table, metrics.duration_ms, consumed_rcu=metrics.consumed_rcu
        )
        return items, metrics

    async def async_parallel_scan(
        self,
        table: str,
        total_segments: int,
        filter_expression: str | None = None,
        projection_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
        consistent_read: bool = False,
    ) -> tuple[list[dict[str, Any]], OperationMetrics]:
        """Async parallel scan - runs multiple segment scans concurrently.

        Much faster than regular scan for large tables. Each segment is
        scanned in parallel using tokio tasks in Rust.

        Args:
            table: Table name.
            total_segments: Number of parallel segments (1-1000000).
            filter_expression: Optional filter expression.
            projection_expression: Optional projection expression (saves RCU).
            expression_attribute_names: Attribute name placeholders.
            expression_attribute_values: Attribute value placeholders.
            consistent_read: Use strongly consistent reads.

        Returns:
            Tuple of (items, metrics) where items is a list of all scanned items.

        Example:
            >>> items, metrics = await client.async_parallel_scan("users", total_segments=4)
            >>> print(f"Found {len(items)} items in {metrics.duration_ms:.2f}ms")
        """
        result = await self._client.async_parallel_scan(  # type: ignore[attr-defined]
            table,
            total_segments,
            filter_expression=filter_expression,
            projection_expression=projection_expression,
            expression_attribute_names=expression_attribute_names,
            expression_attribute_values=expression_attribute_values,
            consistent_read=consistent_read,
        )
        items: list[dict[str, Any]] = result["items"]
        metrics: OperationMetrics = result["metrics"]
        _log_operation(
            "parallel_scan", table, metrics.duration_ms, consumed_rcu=metrics.consumed_rcu
        )
        return items, metrics
