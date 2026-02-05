"""CRUD operations: get, put, delete, update (sync + async)."""

from __future__ import annotations

from typing import Any

from pydynox._internal._logging import _log_debug, _log_operation, _log_warning
from pydynox._internal._metrics import OperationMetrics
from pydynox._internal._tracing import add_response_attributes, trace_operation

_SLOW_QUERY_THRESHOLD_MS = 100.0


def _build_projection(
    projection: list[str] | None,
) -> tuple[str | None, dict[str, str] | None]:
    """Build projection expression and attribute names from a list of fields.

    Handles reserved words by using placeholders (#p0, #p1, etc).
    Supports nested attributes with dot notation.

    Args:
        projection: List of attribute names to project.

    Returns:
        Tuple of (projection_expression, expression_attribute_names).
        Both are None if projection is None or empty.

    Example:
        >>> _build_projection(["name", "address.city"])
        ("#p0, #p1.#p2", {"#p0": "name", "#p1": "address", "#p2": "city"})
    """
    if not projection:
        return None, None

    attr_names: dict[str, str] = {}
    placeholders: list[str] = []
    counter = 0

    for field in projection:
        # Handle nested attributes (e.g., "address.city")
        parts = field.split(".")
        part_placeholders = []
        for part in parts:
            placeholder = f"#p{counter}"
            attr_names[placeholder] = part
            part_placeholders.append(placeholder)
            counter += 1
        placeholders.append(".".join(part_placeholders))

    return ", ".join(placeholders), attr_names


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

    def _record_metrics(self, metrics: OperationMetrics, operation: str) -> None:
        """Record metrics for an operation."""
        self._last_metrics = metrics
        self._total_metrics.add(metrics, operation)  # type: ignore[attr-defined]

    # ========== PUT ==========

    async def put_item(
        self,
        table: str,
        item: dict[str, Any],
        condition_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
        return_values_on_condition_check_failure: bool = False,
    ) -> OperationMetrics:
        """Put an item into a DynamoDB table (async).

        Args:
            table: Table name.
            item: Item to put.
            condition_expression: Condition that must be true for the write.
            expression_attribute_names: Attribute name placeholders.
            expression_attribute_values: Attribute value placeholders.
            return_values_on_condition_check_failure: If True and condition fails,
                the ConditionalCheckFailedException will have an 'item' attribute.

        Returns:
            Operation metrics.
        """
        self._acquire_wcu(1.0)  # type: ignore[attr-defined]
        pk = _extract_pk(item)
        if pk:
            self._record_write(table, pk)  # type: ignore[attr-defined]

        _log_debug("put_item", f'Saving item to "{table}" pk={pk}')

        with trace_operation("put_item", table, self.get_region()) as span:  # type: ignore[attr-defined]
            metrics = await self._client.put_item(  # type: ignore[attr-defined]
                table,
                item,
                condition_expression=condition_expression,
                expression_attribute_names=expression_attribute_names,
                expression_attribute_values=expression_attribute_values,
                return_values_on_condition_check_failure=return_values_on_condition_check_failure,
            )
            add_response_attributes(
                span, consumed_wcu=metrics.consumed_wcu, request_id=metrics.request_id
            )

        _log_operation("put_item", table, metrics.duration_ms, consumed_wcu=metrics.consumed_wcu)
        if metrics.duration_ms > _SLOW_QUERY_THRESHOLD_MS:
            _log_warning("put_item", f"slow operation ({metrics.duration_ms:.1f}ms)")
        self._record_metrics(metrics, "put")
        return metrics

    def sync_put_item(
        self,
        table: str,
        item: dict[str, Any],
        condition_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
        return_values_on_condition_check_failure: bool = False,
    ) -> OperationMetrics:
        """Put an item into a DynamoDB table (sync).

        Args:
            table: Table name.
            item: Item to put.
            condition_expression: Condition that must be true for the write.
            expression_attribute_names: Attribute name placeholders.
            expression_attribute_values: Attribute value placeholders.
            return_values_on_condition_check_failure: If True and condition fails,
                the ConditionalCheckFailedException will have an 'item' attribute
                with the existing item. Saves an extra GET call.

        Returns:
            Operation metrics.

        Raises:
            ConditionalCheckFailedException: If condition fails. When
                return_values_on_condition_check_failure=True, the exception
                has an 'item' attribute with the existing item.
        """
        self._acquire_wcu(1.0)  # type: ignore[attr-defined]
        pk = _extract_pk(item)
        if pk:
            self._record_write(table, pk)  # type: ignore[attr-defined]

        _log_debug("sync_put_item", f'Saving item to "{table}" pk={pk}')

        with trace_operation("put_item", table, self.get_region()) as span:  # type: ignore[attr-defined]
            metrics = self._client.sync_put_item(  # type: ignore[attr-defined]
                table,
                item,
                condition_expression=condition_expression,
                expression_attribute_names=expression_attribute_names,
                expression_attribute_values=expression_attribute_values,
                return_values_on_condition_check_failure=return_values_on_condition_check_failure,
            )
            add_response_attributes(
                span, consumed_wcu=metrics.consumed_wcu, request_id=metrics.request_id
            )

        _log_operation("put_item", table, metrics.duration_ms, consumed_wcu=metrics.consumed_wcu)
        if metrics.duration_ms > _SLOW_QUERY_THRESHOLD_MS:
            _log_warning("put_item", f"slow operation ({metrics.duration_ms:.1f}ms)")
        self._record_metrics(metrics, "put")
        return metrics

    # ========== GET ==========

    async def get_item(
        self,
        table: str,
        key: dict[str, Any],
        consistent_read: bool = False,
        projection: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """Get an item from a DynamoDB table by its key (async).

        Args:
            table: Table name.
            key: Key attributes as a dict.
            consistent_read: Use strongly consistent read.
            projection: List of attributes to return. Saves RCU.

        Returns:
            The item as a dict, or None if not found.
        """
        self._acquire_rcu(1.0)  # type: ignore[attr-defined]
        pk = _extract_pk(key)
        if pk:
            self._record_read(table, pk)  # type: ignore[attr-defined]

        _log_debug("get_item", f'Getting item from "{table}" key={key}')

        # Build projection expression
        projection_expr, attr_names = _build_projection(projection)

        with trace_operation("get_item", table, self.get_region()) as span:  # type: ignore[attr-defined]
            result = await self._client.get_item(  # type: ignore[attr-defined]
                table,
                key,
                consistent_read=consistent_read,
                projection=projection_expr,
                expression_attribute_names=attr_names,
            )
            metrics = result["metrics"]
            add_response_attributes(
                span, consumed_rcu=metrics.consumed_rcu, request_id=metrics.request_id
            )

        _log_operation("get_item", table, metrics.duration_ms, consumed_rcu=metrics.consumed_rcu)
        if metrics.duration_ms > _SLOW_QUERY_THRESHOLD_MS:
            _log_warning("get_item", f"slow operation ({metrics.duration_ms:.1f}ms)")
        self._record_metrics(metrics, "get")
        return result["item"]

    def sync_get_item(
        self,
        table: str,
        key: dict[str, Any],
        consistent_read: bool = False,
        projection: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """Get an item from a DynamoDB table by its key (sync).

        Args:
            table: Table name.
            key: Key attributes as a dict.
            consistent_read: Use strongly consistent read.
            projection: List of attributes to return. Saves RCU by fetching only
                what you need. Use dot notation for nested: ["name", "address.city"].

        Returns:
            The item as a dict, or None if not found.

        Example:
            >>> item = client.sync_get_item("users", {"pk": "USER#1"}, projection=["name", "email"])
        """
        self._acquire_rcu(1.0)  # type: ignore[attr-defined]
        pk = _extract_pk(key)
        if pk:
            self._record_read(table, pk)  # type: ignore[attr-defined]

        _log_debug("sync_get_item", f'Getting item from "{table}" key={key}')

        # Build projection expression
        projection_expr, attr_names = _build_projection(projection)

        with trace_operation("get_item", table, self.get_region()) as span:  # type: ignore[attr-defined]
            result, metrics = self._client.sync_get_item(  # type: ignore[attr-defined]
                table,
                key,
                consistent_read=consistent_read,
                projection=projection_expr,
                expression_attribute_names=attr_names,
            )
            add_response_attributes(
                span, consumed_rcu=metrics.consumed_rcu, request_id=metrics.request_id
            )

        self._record_metrics(metrics, "get")
        _log_operation("get_item", table, metrics.duration_ms, consumed_rcu=metrics.consumed_rcu)
        if metrics.duration_ms > _SLOW_QUERY_THRESHOLD_MS:
            _log_warning("get_item", f"slow operation ({metrics.duration_ms:.1f}ms)")
        return result

    # ========== DELETE ==========

    async def delete_item(
        self,
        table: str,
        key: dict[str, Any],
        condition_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
        return_values_on_condition_check_failure: bool = False,
    ) -> OperationMetrics:
        """Delete an item from a DynamoDB table (async).

        Args:
            table: Table name.
            key: Key attributes.
            condition_expression: Condition that must be true for the delete.
            expression_attribute_names: Attribute name placeholders.
            expression_attribute_values: Attribute value placeholders.
            return_values_on_condition_check_failure: If True and condition fails,
                the ConditionalCheckFailedException will have an 'item' attribute.

        Returns:
            Operation metrics.
        """
        self._acquire_wcu(1.0)  # type: ignore[attr-defined]
        pk = _extract_pk(key)
        if pk:
            self._record_write(table, pk)  # type: ignore[attr-defined]

        _log_debug("delete_item", f'Deleting item from "{table}" key={key}')

        with trace_operation("delete_item", table, self.get_region()) as span:  # type: ignore[attr-defined]
            metrics = await self._client.delete_item(  # type: ignore[attr-defined]
                table,
                key,
                condition_expression=condition_expression,
                expression_attribute_names=expression_attribute_names,
                expression_attribute_values=expression_attribute_values,
                return_values_on_condition_check_failure=return_values_on_condition_check_failure,
            )
            add_response_attributes(
                span, consumed_wcu=metrics.consumed_wcu, request_id=metrics.request_id
            )

        _log_operation("delete_item", table, metrics.duration_ms, consumed_wcu=metrics.consumed_wcu)
        if metrics.duration_ms > _SLOW_QUERY_THRESHOLD_MS:
            _log_warning("delete_item", f"slow operation ({metrics.duration_ms:.1f}ms)")
        self._record_metrics(metrics, "delete")
        return metrics

    def sync_delete_item(
        self,
        table: str,
        key: dict[str, Any],
        condition_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
        return_values_on_condition_check_failure: bool = False,
    ) -> OperationMetrics:
        """Delete an item from a DynamoDB table (sync).

        Args:
            table: Table name.
            key: Key attributes.
            condition_expression: Condition that must be true for the delete.
            expression_attribute_names: Attribute name placeholders.
            expression_attribute_values: Attribute value placeholders.
            return_values_on_condition_check_failure: If True and condition fails,
                the ConditionalCheckFailedException will have an 'item' attribute.

        Returns:
            Operation metrics.
        """
        self._acquire_wcu(1.0)  # type: ignore[attr-defined]
        pk = _extract_pk(key)
        if pk:
            self._record_write(table, pk)  # type: ignore[attr-defined]

        _log_debug("sync_delete_item", f'Deleting item from "{table}" key={key}')

        with trace_operation("delete_item", table, self.get_region()) as span:  # type: ignore[attr-defined]
            metrics = self._client.sync_delete_item(  # type: ignore[attr-defined]
                table,
                key,
                condition_expression=condition_expression,
                expression_attribute_names=expression_attribute_names,
                expression_attribute_values=expression_attribute_values,
                return_values_on_condition_check_failure=return_values_on_condition_check_failure,
            )
            add_response_attributes(
                span, consumed_wcu=metrics.consumed_wcu, request_id=metrics.request_id
            )

        _log_operation("delete_item", table, metrics.duration_ms, consumed_wcu=metrics.consumed_wcu)
        if metrics.duration_ms > _SLOW_QUERY_THRESHOLD_MS:
            _log_warning("delete_item", f"slow operation ({metrics.duration_ms:.1f}ms)")
        self._record_metrics(metrics, "delete")
        return metrics

    # ========== UPDATE ==========

    async def update_item(
        self,
        table: str,
        key: dict[str, Any],
        updates: dict[str, Any] | None = None,
        update_expression: str | None = None,
        condition_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
        return_values_on_condition_check_failure: bool = False,
    ) -> OperationMetrics:
        """Update an item in a DynamoDB table (async).

        Args:
            table: Table name.
            key: Key attributes.
            updates: Dict of field:value pairs to update (simple mode).
            update_expression: Raw update expression (advanced mode).
            condition_expression: Condition that must be true for the update.
            expression_attribute_names: Attribute name placeholders.
            expression_attribute_values: Attribute value placeholders.
            return_values_on_condition_check_failure: If True and condition fails,
                the ConditionalCheckFailedException will have an 'item' attribute.

        Returns:
            Operation metrics.
        """
        self._acquire_wcu(1.0)  # type: ignore[attr-defined]
        pk = _extract_pk(key)
        if pk:
            self._record_write(table, pk)  # type: ignore[attr-defined]

        _log_debug("update_item", f'Updating item in "{table}" key={key}')

        with trace_operation("update_item", table, self.get_region()) as span:  # type: ignore[attr-defined]
            metrics = await self._client.update_item(  # type: ignore[attr-defined]
                table,
                key,
                updates=updates,
                update_expression=update_expression,
                condition_expression=condition_expression,
                expression_attribute_names=expression_attribute_names,
                expression_attribute_values=expression_attribute_values,
                return_values_on_condition_check_failure=return_values_on_condition_check_failure,
            )
            add_response_attributes(
                span, consumed_wcu=metrics.consumed_wcu, request_id=metrics.request_id
            )

        _log_operation("update_item", table, metrics.duration_ms, consumed_wcu=metrics.consumed_wcu)
        if metrics.duration_ms > _SLOW_QUERY_THRESHOLD_MS:
            _log_warning("update_item", f"slow operation ({metrics.duration_ms:.1f}ms)")
        self._record_metrics(metrics, "update")
        return metrics

    def sync_update_item(
        self,
        table: str,
        key: dict[str, Any],
        updates: dict[str, Any] | None = None,
        update_expression: str | None = None,
        condition_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
        return_values_on_condition_check_failure: bool = False,
    ) -> OperationMetrics:
        """Update an item in a DynamoDB table (sync).

        Args:
            table: Table name.
            key: Key attributes.
            updates: Dict of field:value pairs to update (simple mode).
            update_expression: Raw update expression (advanced mode).
            condition_expression: Condition that must be true for the update.
            expression_attribute_names: Attribute name placeholders.
            expression_attribute_values: Attribute value placeholders.
            return_values_on_condition_check_failure: If True and condition fails,
                the ConditionalCheckFailedException will have an 'item' attribute.

        Returns:
            Operation metrics.
        """
        self._acquire_wcu(1.0)  # type: ignore[attr-defined]
        pk = _extract_pk(key)
        if pk:
            self._record_write(table, pk)  # type: ignore[attr-defined]

        _log_debug("sync_update_item", f'Updating item in "{table}" key={key}')

        with trace_operation("update_item", table, self.get_region()) as span:  # type: ignore[attr-defined]
            metrics = self._client.sync_update_item(  # type: ignore[attr-defined]
                table,
                key,
                updates=updates,
                update_expression=update_expression,
                condition_expression=condition_expression,
                expression_attribute_names=expression_attribute_names,
                expression_attribute_values=expression_attribute_values,
                return_values_on_condition_check_failure=return_values_on_condition_check_failure,
            )
            add_response_attributes(
                span, consumed_wcu=metrics.consumed_wcu, request_id=metrics.request_id
            )

        _log_operation("update_item", table, metrics.duration_ms, consumed_wcu=metrics.consumed_wcu)
        if metrics.duration_ms > _SLOW_QUERY_THRESHOLD_MS:
            _log_warning("update_item", f"slow operation ({metrics.duration_ms:.1f}ms)")
        self._record_metrics(metrics, "update")
        return metrics
