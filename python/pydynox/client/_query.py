"""Query operations (sync + async)."""

from __future__ import annotations

from typing import Any

from pydynox.query import AsyncQueryResult, QueryResult


class QueryOperations:
    """Query operations."""

    def sync_query(
        self,
        table: str,
        key_condition_expression: str,
        filter_expression: str | None = None,
        projection_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
        limit: int | None = None,
        page_size: int | None = None,
        scan_index_forward: bool | None = None,
        index_name: str | None = None,
        last_evaluated_key: dict[str, Any] | None = None,
        consistent_read: bool = False,
    ) -> QueryResult:
        """Query items from a DynamoDB table (sync).

        Args:
            table: Table name.
            key_condition_expression: Key condition expression.
            filter_expression: Optional filter expression.
            projection_expression: Optional projection expression (saves RCU).
            expression_attribute_names: Attribute name placeholders.
            expression_attribute_values: Attribute value placeholders.
            limit: Max total items to return.
            page_size: Items per page (passed as Limit to DynamoDB).
            scan_index_forward: Sort order (True = ascending).
            index_name: GSI or LSI name.
            last_evaluated_key: Start key for pagination.
            consistent_read: Use strongly consistent read.

        Returns:
            QueryResult iterator.
        """
        return QueryResult(
            self._client,  # type: ignore[attr-defined]
            table,
            key_condition_expression,
            filter_expression=filter_expression,
            projection_expression=projection_expression,
            expression_attribute_names=expression_attribute_names,
            expression_attribute_values=expression_attribute_values,
            limit=limit,
            page_size=page_size,
            scan_index_forward=scan_index_forward,
            index_name=index_name,
            last_evaluated_key=last_evaluated_key,
            acquire_rcu=self._acquire_rcu,  # type: ignore[attr-defined]
            consistent_read=consistent_read,
        )

    def query(
        self,
        table: str,
        key_condition_expression: str,
        filter_expression: str | None = None,
        projection_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
        limit: int | None = None,
        page_size: int | None = None,
        scan_index_forward: bool | None = None,
        index_name: str | None = None,
        last_evaluated_key: dict[str, Any] | None = None,
        consistent_read: bool = False,
    ) -> AsyncQueryResult:
        """Query items from a DynamoDB table (async).

        Args:
            table: Table name.
            key_condition_expression: Key condition expression.
            filter_expression: Optional filter expression.
            projection_expression: Optional projection expression (saves RCU).
            expression_attribute_names: Attribute name placeholders.
            expression_attribute_values: Attribute value placeholders.
            limit: Max total items to return.
            page_size: Items per page (passed as Limit to DynamoDB).
            scan_index_forward: Sort order (True = ascending).
            index_name: GSI or LSI name.
            last_evaluated_key: Start key for pagination.
            consistent_read: Use strongly consistent read.

        Returns:
            AsyncQueryResult iterator.
        """
        return AsyncQueryResult(
            self._client,  # type: ignore[attr-defined]
            table,
            key_condition_expression,
            filter_expression=filter_expression,
            projection_expression=projection_expression,
            expression_attribute_names=expression_attribute_names,
            expression_attribute_values=expression_attribute_values,
            limit=limit,
            page_size=page_size,
            scan_index_forward=scan_index_forward,
            index_name=index_name,
            last_evaluated_key=last_evaluated_key,
            acquire_rcu=self._acquire_rcu,  # type: ignore[attr-defined]
            consistent_read=consistent_read,
        )
