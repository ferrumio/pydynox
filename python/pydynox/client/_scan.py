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
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
        limit: int | None = None,
        index_name: str | None = None,
        last_evaluated_key: dict[str, Any] | None = None,
        consistent_read: bool = False,
        segment: int | None = None,
        total_segments: int | None = None,
    ) -> ScanResult:
        """Scan items from a DynamoDB table."""
        return ScanResult(
            self._client,  # type: ignore[attr-defined]
            table,
            filter_expression=filter_expression,
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
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
        limit: int | None = None,
        index_name: str | None = None,
        last_evaluated_key: dict[str, Any] | None = None,
        consistent_read: bool = False,
        segment: int | None = None,
        total_segments: int | None = None,
    ) -> AsyncScanResult:
        """Async scan items from a DynamoDB table."""
        return AsyncScanResult(
            self._client,  # type: ignore[attr-defined]
            table,
            filter_expression=filter_expression,
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
