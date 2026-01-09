"""CRUD operations: get, put, delete, update (sync + async)."""

from __future__ import annotations

from typing import Any

from pydynox._internal._logging import _log_operation, _log_warning
from pydynox._internal._metrics import DictWithMetrics, OperationMetrics
from pydynox._internal._tracing import add_response_attributes, trace_operation

_SLOW_QUERY_THRESHOLD_MS = 100.0


def _extract_pk(item_or_key: dict[str, Any]) -> str | None:
    """Extract partition key value from item or key dict.

    Returns the first key's value as string, or None if empty.
    """
    if not item_or_key:
        return None
    first_key = next(iter(item_or_key))
    value = item_or_key[first_key]
    return str(value) if value is not None else None


class CrudOperations:
    """CRUD operations: get, put, delete, update."""

    # ========== PUT ==========

    def put_item(
        self,
        table: str,
        item: dict[str, Any],
        condition_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
    ) -> OperationMetrics:
        """Put an item into a DynamoDB table."""
        self._acquire_wcu(1.0)  # type: ignore[attr-defined]
        pk = _extract_pk(item)
        if pk:
            self._record_write(table, pk)  # type: ignore[attr-defined]

        with trace_operation("put_item", table, self.get_region()) as span:  # type: ignore[attr-defined]
            metrics = self._client.put_item(  # type: ignore[attr-defined]
                table,
                item,
                condition_expression=condition_expression,
                expression_attribute_names=expression_attribute_names,
                expression_attribute_values=expression_attribute_values,
            )
            add_response_attributes(
                span, consumed_wcu=metrics.consumed_wcu, request_id=metrics.request_id
            )

        _log_operation("put_item", table, metrics.duration_ms, consumed_wcu=metrics.consumed_wcu)
        if metrics.duration_ms > _SLOW_QUERY_THRESHOLD_MS:
            _log_warning("put_item", f"slow operation ({metrics.duration_ms:.1f}ms)")
        return metrics  # type: ignore[no-any-return]

    async def async_put_item(
        self,
        table: str,
        item: dict[str, Any],
        condition_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
    ) -> OperationMetrics:
        """Async version of put_item."""
        self._acquire_wcu(1.0)  # type: ignore[attr-defined]
        pk = _extract_pk(item)
        if pk:
            self._record_write(table, pk)  # type: ignore[attr-defined]

        with trace_operation("async_put_item", table, self.get_region()) as span:  # type: ignore[attr-defined]
            metrics = await self._client.async_put_item(  # type: ignore[attr-defined]
                table,
                item,
                condition_expression=condition_expression,
                expression_attribute_names=expression_attribute_names,
                expression_attribute_values=expression_attribute_values,
            )
            add_response_attributes(
                span, consumed_wcu=metrics.consumed_wcu, request_id=metrics.request_id
            )

        _log_operation("put_item", table, metrics.duration_ms, consumed_wcu=metrics.consumed_wcu)
        if metrics.duration_ms > _SLOW_QUERY_THRESHOLD_MS:
            _log_warning("put_item", f"slow operation ({metrics.duration_ms:.1f}ms)")
        return metrics  # type: ignore[no-any-return]

    # ========== GET ==========

    def get_item(
        self, table: str, key: dict[str, Any], consistent_read: bool = False
    ) -> DictWithMetrics | None:
        """Get an item from a DynamoDB table by its key."""
        self._acquire_rcu(1.0)  # type: ignore[attr-defined]
        pk = _extract_pk(key)
        if pk:
            self._record_read(table, pk)  # type: ignore[attr-defined]

        with trace_operation("get_item", table, self.get_region()) as span:  # type: ignore[attr-defined]
            result, metrics = self._client.get_item(  # type: ignore[attr-defined]
                table, key, consistent_read=consistent_read
            )
            add_response_attributes(
                span, consumed_rcu=metrics.consumed_rcu, request_id=metrics.request_id
            )

        _log_operation("get_item", table, metrics.duration_ms, consumed_rcu=metrics.consumed_rcu)
        if metrics.duration_ms > _SLOW_QUERY_THRESHOLD_MS:
            _log_warning("get_item", f"slow operation ({metrics.duration_ms:.1f}ms)")
        if result is None:
            return None
        return DictWithMetrics(result, metrics)

    async def async_get_item(
        self, table: str, key: dict[str, Any], consistent_read: bool = False
    ) -> DictWithMetrics | None:
        """Async version of get_item."""
        self._acquire_rcu(1.0)  # type: ignore[attr-defined]
        pk = _extract_pk(key)
        if pk:
            self._record_read(table, pk)  # type: ignore[attr-defined]

        with trace_operation("async_get_item", table, self.get_region()) as span:  # type: ignore[attr-defined]
            result = await self._client.async_get_item(  # type: ignore[attr-defined]
                table, key, consistent_read=consistent_read
            )
            metrics = result["metrics"]
            add_response_attributes(
                span, consumed_rcu=metrics.consumed_rcu, request_id=metrics.request_id
            )

        _log_operation("get_item", table, metrics.duration_ms, consumed_rcu=metrics.consumed_rcu)
        if metrics.duration_ms > _SLOW_QUERY_THRESHOLD_MS:
            _log_warning("get_item", f"slow operation ({metrics.duration_ms:.1f}ms)")
        if result["item"] is None:
            return None
        return DictWithMetrics(result["item"], metrics)

    # ========== DELETE ==========

    def delete_item(
        self,
        table: str,
        key: dict[str, Any],
        condition_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
    ) -> OperationMetrics:
        """Delete an item from a DynamoDB table."""
        self._acquire_wcu(1.0)  # type: ignore[attr-defined]
        pk = _extract_pk(key)
        if pk:
            self._record_write(table, pk)  # type: ignore[attr-defined]

        with trace_operation("delete_item", table, self.get_region()) as span:  # type: ignore[attr-defined]
            metrics = self._client.delete_item(  # type: ignore[attr-defined]
                table,
                key,
                condition_expression=condition_expression,
                expression_attribute_names=expression_attribute_names,
                expression_attribute_values=expression_attribute_values,
            )
            add_response_attributes(
                span, consumed_wcu=metrics.consumed_wcu, request_id=metrics.request_id
            )

        _log_operation("delete_item", table, metrics.duration_ms, consumed_wcu=metrics.consumed_wcu)
        if metrics.duration_ms > _SLOW_QUERY_THRESHOLD_MS:
            _log_warning("delete_item", f"slow operation ({metrics.duration_ms:.1f}ms)")
        return metrics  # type: ignore[no-any-return]

    async def async_delete_item(
        self,
        table: str,
        key: dict[str, Any],
        condition_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
    ) -> OperationMetrics:
        """Async version of delete_item."""
        self._acquire_wcu(1.0)  # type: ignore[attr-defined]
        pk = _extract_pk(key)
        if pk:
            self._record_write(table, pk)  # type: ignore[attr-defined]

        with trace_operation("async_delete_item", table, self.get_region()) as span:  # type: ignore[attr-defined]
            metrics = await self._client.async_delete_item(  # type: ignore[attr-defined]
                table,
                key,
                condition_expression=condition_expression,
                expression_attribute_names=expression_attribute_names,
                expression_attribute_values=expression_attribute_values,
            )
            add_response_attributes(
                span, consumed_wcu=metrics.consumed_wcu, request_id=metrics.request_id
            )

        _log_operation("delete_item", table, metrics.duration_ms, consumed_wcu=metrics.consumed_wcu)
        if metrics.duration_ms > _SLOW_QUERY_THRESHOLD_MS:
            _log_warning("delete_item", f"slow operation ({metrics.duration_ms:.1f}ms)")
        return metrics  # type: ignore[no-any-return]

    # ========== UPDATE ==========

    def update_item(
        self,
        table: str,
        key: dict[str, Any],
        updates: dict[str, Any] | None = None,
        update_expression: str | None = None,
        condition_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
    ) -> OperationMetrics:
        """Update an item in a DynamoDB table."""
        self._acquire_wcu(1.0)  # type: ignore[attr-defined]
        pk = _extract_pk(key)
        if pk:
            self._record_write(table, pk)  # type: ignore[attr-defined]

        with trace_operation("update_item", table, self.get_region()) as span:  # type: ignore[attr-defined]
            metrics = self._client.update_item(  # type: ignore[attr-defined]
                table,
                key,
                updates=updates,
                update_expression=update_expression,
                condition_expression=condition_expression,
                expression_attribute_names=expression_attribute_names,
                expression_attribute_values=expression_attribute_values,
            )
            add_response_attributes(
                span, consumed_wcu=metrics.consumed_wcu, request_id=metrics.request_id
            )

        _log_operation("update_item", table, metrics.duration_ms, consumed_wcu=metrics.consumed_wcu)
        if metrics.duration_ms > _SLOW_QUERY_THRESHOLD_MS:
            _log_warning("update_item", f"slow operation ({metrics.duration_ms:.1f}ms)")
        return metrics  # type: ignore[no-any-return]

    async def async_update_item(
        self,
        table: str,
        key: dict[str, Any],
        updates: dict[str, Any] | None = None,
        update_expression: str | None = None,
        condition_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
    ) -> OperationMetrics:
        """Async version of update_item."""
        self._acquire_wcu(1.0)  # type: ignore[attr-defined]
        pk = _extract_pk(key)
        if pk:
            self._record_write(table, pk)  # type: ignore[attr-defined]

        with trace_operation("async_update_item", table, self.get_region()) as span:  # type: ignore[attr-defined]
            metrics = await self._client.async_update_item(  # type: ignore[attr-defined]
                table,
                key,
                updates=updates,
                update_expression=update_expression,
                condition_expression=condition_expression,
                expression_attribute_names=expression_attribute_names,
                expression_attribute_values=expression_attribute_values,
            )
            add_response_attributes(
                span, consumed_wcu=metrics.consumed_wcu, request_id=metrics.request_id
            )

        _log_operation("update_item", table, metrics.duration_ms, consumed_wcu=metrics.consumed_wcu)
        if metrics.duration_ms > _SLOW_QUERY_THRESHOLD_MS:
            _log_warning("update_item", f"slow operation ({metrics.duration_ms:.1f}ms)")
        return metrics  # type: ignore[no-any-return]
