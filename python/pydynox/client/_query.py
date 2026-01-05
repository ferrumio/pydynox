"""Query operations (sync + async)."""

from __future__ import annotations

from typing import Any

from pydynox.query import AsyncQueryResult, QueryResult


class QueryOperations:
    """Query operations."""

    def query(
        self,
        table: str,
        key_condition_expression: str,
        filter_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
        limit: int | None = None,
        scan_index_forward: bool | None = None,
        index_name: str | None = None,
        last_evaluated_key: dict[str, Any] | None = None,
        consistent_read: bool = False,
    ) -> QueryResult:
        """Query items from a DynamoDB table."""
        return QueryResult(
            self._client,  # type: ignore[attr-defined]
            table,
            key_condition_expression,
            filter_expression=filter_expression,
            expression_attribute_names=expression_attribute_names,
            expression_attribute_values=expression_attribute_values,
            limit=limit,
            scan_index_forward=scan_index_forward,
            index_name=index_name,
            last_evaluated_key=last_evaluated_key,
            acquire_rcu=self._acquire_rcu,  # type: ignore[attr-defined]
            consistent_read=consistent_read,
        )

    def async_query(
        self,
        table: str,
        key_condition_expression: str,
        filter_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
        limit: int | None = None,
        scan_index_forward: bool | None = None,
        index_name: str | None = None,
        last_evaluated_key: dict[str, Any] | None = None,
        consistent_read: bool = False,
    ) -> AsyncQueryResult:
        """Async query items from a DynamoDB table."""
        return AsyncQueryResult(
            self._client,  # type: ignore[attr-defined]
            table,
            key_condition_expression,
            filter_expression=filter_expression,
            expression_attribute_names=expression_attribute_names,
            expression_attribute_values=expression_attribute_values,
            limit=limit,
            scan_index_forward=scan_index_forward,
            index_name=index_name,
            last_evaluated_key=last_evaluated_key,
            acquire_rcu=self._acquire_rcu,  # type: ignore[attr-defined]
            consistent_read=consistent_read,
        )
