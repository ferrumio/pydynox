"""Query result and pagination."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from pydynox._internal._logging import _log_operation, _log_warning

if TYPE_CHECKING:
    from pydynox import pydynox_core
    from pydynox._internal._metrics import OperationMetrics

# Threshold for slow query warning (ms)
_SLOW_QUERY_THRESHOLD_MS = 100.0


class QueryResult:
    """Result of a DynamoDB query with automatic pagination.

    Iterate over results and access `last_evaluated_key` for manual pagination.

    Example:
        >>> results = client.query("users", key_condition_expression="pk = :pk", ...)
        >>> for item in results:
        ...     print(item["name"])
    """

    def __init__(
        self,
        client: pydynox_core.DynamoDBClient,
        table: str,
        key_condition_expression: str,
        filter_expression: str | None = None,
        projection_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
        limit: int | None = None,
        scan_index_forward: bool | None = None,
        index_name: str | None = None,
        last_evaluated_key: dict[str, Any] | None = None,
        acquire_rcu: Callable[[float], None] | None = None,
        consistent_read: bool = False,
    ):
        self._client = client
        self._table = table
        self._key_condition_expression = key_condition_expression
        self._filter_expression = filter_expression
        self._projection_expression = projection_expression
        self._expression_attribute_names = expression_attribute_names
        self._expression_attribute_values = expression_attribute_values
        self._limit = limit
        self._scan_index_forward = scan_index_forward
        self._index_name = index_name
        self._start_key = last_evaluated_key
        self._acquire_rcu = acquire_rcu
        self._consistent_read = consistent_read

        self._current_page: list[dict[str, Any]] = []
        self._page_index = 0
        self._last_evaluated_key: dict[str, Any] | None = None
        self._exhausted = False
        self._first_fetch = True
        self._metrics: OperationMetrics | None = None

    @property
    def last_evaluated_key(self) -> dict[str, Any] | None:
        """The last evaluated key for pagination.

        Returns None if all results have been fetched.
        Use this to continue pagination in a new query.
        """
        return self._last_evaluated_key

    def __iter__(self) -> "QueryResult":
        return self

    def __next__(self) -> dict[str, Any]:
        # If we have items in current page, return next one
        if self._page_index < len(self._current_page):
            item = self._current_page[self._page_index]
            self._page_index += 1
            return item

        # If exhausted, stop
        if self._exhausted:
            raise StopIteration

        # Fetch next page
        self._fetch_next_page()

        # If no items after fetch, stop
        if not self._current_page:
            raise StopIteration

        item = self._current_page[self._page_index]
        self._page_index += 1
        return item

    def _fetch_next_page(self) -> None:
        """Fetch the next page of results from DynamoDB."""
        # Don't fetch if we know there are no more pages
        if not self._first_fetch and self._last_evaluated_key is None:
            self._exhausted = True
            return

        # Use start_key on first fetch, then last_evaluated_key
        start_key = self._start_key if self._first_fetch else self._last_evaluated_key
        self._first_fetch = False

        # Acquire RCU before fetching (estimate based on limit or default)
        if self._acquire_rcu is not None:
            rcu_estimate = float(self._limit) if self._limit else 1.0
            self._acquire_rcu(rcu_estimate)

        items, self._last_evaluated_key, self._metrics = self._client.query_page(
            self._table,
            self._key_condition_expression,
            filter_expression=self._filter_expression,
            projection_expression=self._projection_expression,
            expression_attribute_names=self._expression_attribute_names,
            expression_attribute_values=self._expression_attribute_values,
            limit=self._limit,
            exclusive_start_key=start_key,
            scan_index_forward=self._scan_index_forward,
            index_name=self._index_name,
            consistent_read=self._consistent_read,
        )

        self._current_page = items
        self._page_index = 0

        # Log the query
        _log_operation(
            "query",
            self._table,
            self._metrics.duration_ms,
            consumed_rcu=self._metrics.consumed_rcu,
            items_count=self._metrics.items_count,
        )
        if self._metrics.duration_ms > _SLOW_QUERY_THRESHOLD_MS:
            _log_warning("query", f"slow operation ({self._metrics.duration_ms:.1f}ms)")

        # If no last_key, this is the final page
        if self._last_evaluated_key is None:
            self._exhausted = True


class AsyncQueryResult:
    """Async result of a DynamoDB query with automatic pagination.

    Use `async for` to iterate over results.

    Example:
        >>> async for item in client.async_query("users", ...):
        ...     print(item["name"])
    """

    def __init__(
        self,
        client: pydynox_core.DynamoDBClient,
        table: str,
        key_condition_expression: str,
        filter_expression: str | None = None,
        projection_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
        limit: int | None = None,
        scan_index_forward: bool | None = None,
        index_name: str | None = None,
        last_evaluated_key: dict[str, Any] | None = None,
        acquire_rcu: Callable[[float], None] | None = None,
        consistent_read: bool = False,
    ):
        self._client = client
        self._table = table
        self._key_condition_expression = key_condition_expression
        self._filter_expression = filter_expression
        self._projection_expression = projection_expression
        self._expression_attribute_names = expression_attribute_names
        self._expression_attribute_values = expression_attribute_values
        self._limit = limit
        self._scan_index_forward = scan_index_forward
        self._index_name = index_name
        self._start_key = last_evaluated_key
        self._acquire_rcu = acquire_rcu
        self._consistent_read = consistent_read

        self._current_page: list[dict[str, Any]] = []
        self._page_index = 0
        self._last_evaluated_key: dict[str, Any] | None = None
        self._exhausted = False
        self._first_fetch = True
        self._metrics: OperationMetrics | None = None

    @property
    def last_evaluated_key(self) -> dict[str, Any] | None:
        """The last evaluated key for pagination."""
        return self._last_evaluated_key

    def __aiter__(self) -> "AsyncQueryResult":
        return self

    async def __anext__(self) -> dict[str, Any]:
        # If we have items in current page, return next one
        if self._page_index < len(self._current_page):
            item = self._current_page[self._page_index]
            self._page_index += 1
            return item

        # If exhausted, stop
        if self._exhausted:
            raise StopAsyncIteration

        # Fetch next page
        await self._fetch_next_page()

        # If no items after fetch, stop
        if not self._current_page:
            raise StopAsyncIteration

        item = self._current_page[self._page_index]
        self._page_index += 1
        return item

    async def _fetch_next_page(self) -> None:
        """Fetch the next page of results from DynamoDB."""
        # Don't fetch if we know there are no more pages
        if not self._first_fetch and self._last_evaluated_key is None:
            self._exhausted = True
            return

        # Use start_key on first fetch, then last_evaluated_key
        start_key = self._start_key if self._first_fetch else self._last_evaluated_key
        self._first_fetch = False

        # Acquire RCU before fetching
        if self._acquire_rcu is not None:
            rcu_estimate = float(self._limit) if self._limit else 1.0
            self._acquire_rcu(rcu_estimate)

        result = await self._client.async_query_page(
            self._table,
            self._key_condition_expression,
            filter_expression=self._filter_expression,
            projection_expression=self._projection_expression,
            expression_attribute_names=self._expression_attribute_names,
            expression_attribute_values=self._expression_attribute_values,
            limit=self._limit,
            exclusive_start_key=start_key,
            scan_index_forward=self._scan_index_forward,
            index_name=self._index_name,
            consistent_read=self._consistent_read,
        )

        self._current_page = result["items"]
        self._last_evaluated_key = result["last_evaluated_key"]
        self._metrics = result["metrics"]
        self._page_index = 0

        # Log the query
        _log_operation(
            "query",
            self._table,
            self._metrics.duration_ms,
            consumed_rcu=self._metrics.consumed_rcu,
            items_count=self._metrics.items_count,
        )
        if self._metrics.duration_ms > _SLOW_QUERY_THRESHOLD_MS:
            _log_warning("query", f"slow operation ({self._metrics.duration_ms:.1f}ms)")

        # If no last_key, this is the final page
        if self._last_evaluated_key is None:
            self._exhausted = True

    async def to_list(self) -> list[dict[str, Any]]:
        """Collect all results into a list.

        Example:
            >>> items = await client.async_query("users", ...).to_list()
        """
        items = []
        async for item in self:
            items.append(item)
        return items


class ScanResult:
    """Result of a DynamoDB scan with automatic pagination.

    Iterate over results and access `last_evaluated_key` for manual pagination.

    Example:
        >>> results = client.scan("users")
        >>> for item in results:
        ...     print(item["name"])
    """

    def __init__(
        self,
        client: pydynox_core.DynamoDBClient,
        table: str,
        filter_expression: str | None = None,
        projection_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
        limit: int | None = None,
        index_name: str | None = None,
        last_evaluated_key: dict[str, Any] | None = None,
        acquire_rcu: Callable[[float], None] | None = None,
        consistent_read: bool = False,
        segment: int | None = None,
        total_segments: int | None = None,
    ):
        self._client = client
        self._table = table
        self._filter_expression = filter_expression
        self._projection_expression = projection_expression
        self._expression_attribute_names = expression_attribute_names
        self._expression_attribute_values = expression_attribute_values
        self._limit = limit
        self._index_name = index_name
        self._start_key = last_evaluated_key
        self._acquire_rcu = acquire_rcu
        self._consistent_read = consistent_read
        self._segment = segment
        self._total_segments = total_segments

        self._current_page: list[dict[str, Any]] = []
        self._page_index = 0
        self._last_evaluated_key: dict[str, Any] | None = None
        self._exhausted = False
        self._first_fetch = True
        self._metrics: OperationMetrics | None = None

    @property
    def last_evaluated_key(self) -> dict[str, Any] | None:
        """The last evaluated key for pagination."""
        return self._last_evaluated_key

    def __iter__(self) -> "ScanResult":
        return self

    def __next__(self) -> dict[str, Any]:
        if self._page_index < len(self._current_page):
            item = self._current_page[self._page_index]
            self._page_index += 1
            return item

        if self._exhausted:
            raise StopIteration

        self._fetch_next_page()

        if not self._current_page:
            raise StopIteration

        item = self._current_page[self._page_index]
        self._page_index += 1
        return item

    def _fetch_next_page(self) -> None:
        """Fetch the next page of results from DynamoDB."""
        if not self._first_fetch and self._last_evaluated_key is None:
            self._exhausted = True
            return

        start_key = self._start_key if self._first_fetch else self._last_evaluated_key
        self._first_fetch = False

        if self._acquire_rcu is not None:
            rcu_estimate = float(self._limit) if self._limit else 1.0
            self._acquire_rcu(rcu_estimate)

        items, self._last_evaluated_key, self._metrics = self._client.scan_page(
            self._table,
            filter_expression=self._filter_expression,
            projection_expression=self._projection_expression,
            expression_attribute_names=self._expression_attribute_names,
            expression_attribute_values=self._expression_attribute_values,
            limit=self._limit,
            exclusive_start_key=start_key,
            index_name=self._index_name,
            consistent_read=self._consistent_read,
            segment=self._segment,
            total_segments=self._total_segments,
        )

        self._current_page = items
        self._page_index = 0

        _log_operation(
            "scan",
            self._table,
            self._metrics.duration_ms,
            consumed_rcu=self._metrics.consumed_rcu,
            items_count=self._metrics.items_count,
        )
        if self._metrics.duration_ms > _SLOW_QUERY_THRESHOLD_MS:
            _log_warning("scan", f"slow operation ({self._metrics.duration_ms:.1f}ms)")

        if self._last_evaluated_key is None:
            self._exhausted = True


class AsyncScanResult:
    """Async result of a DynamoDB scan with automatic pagination.

    Use `async for` to iterate over results.

    Example:
        >>> async for item in client.async_scan("users"):
        ...     print(item["name"])
    """

    def __init__(
        self,
        client: pydynox_core.DynamoDBClient,
        table: str,
        filter_expression: str | None = None,
        projection_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
        limit: int | None = None,
        index_name: str | None = None,
        last_evaluated_key: dict[str, Any] | None = None,
        acquire_rcu: Callable[[float], None] | None = None,
        consistent_read: bool = False,
        segment: int | None = None,
        total_segments: int | None = None,
    ):
        self._client = client
        self._table = table
        self._filter_expression = filter_expression
        self._projection_expression = projection_expression
        self._expression_attribute_names = expression_attribute_names
        self._expression_attribute_values = expression_attribute_values
        self._limit = limit
        self._index_name = index_name
        self._start_key = last_evaluated_key
        self._acquire_rcu = acquire_rcu
        self._consistent_read = consistent_read
        self._segment = segment
        self._total_segments = total_segments

        self._current_page: list[dict[str, Any]] = []
        self._page_index = 0
        self._last_evaluated_key: dict[str, Any] | None = None
        self._exhausted = False
        self._first_fetch = True
        self._metrics: OperationMetrics | None = None

    @property
    def last_evaluated_key(self) -> dict[str, Any] | None:
        """The last evaluated key for pagination."""
        return self._last_evaluated_key

    def __aiter__(self) -> "AsyncScanResult":
        return self

    async def __anext__(self) -> dict[str, Any]:
        if self._page_index < len(self._current_page):
            item = self._current_page[self._page_index]
            self._page_index += 1
            return item

        if self._exhausted:
            raise StopAsyncIteration

        await self._fetch_next_page()

        if not self._current_page:
            raise StopAsyncIteration

        item = self._current_page[self._page_index]
        self._page_index += 1
        return item

    async def _fetch_next_page(self) -> None:
        """Fetch the next page of results from DynamoDB."""
        if not self._first_fetch and self._last_evaluated_key is None:
            self._exhausted = True
            return

        start_key = self._start_key if self._first_fetch else self._last_evaluated_key
        self._first_fetch = False

        if self._acquire_rcu is not None:
            rcu_estimate = float(self._limit) if self._limit else 1.0
            self._acquire_rcu(rcu_estimate)

        result = await self._client.async_scan_page(
            self._table,
            filter_expression=self._filter_expression,
            projection_expression=self._projection_expression,
            expression_attribute_names=self._expression_attribute_names,
            expression_attribute_values=self._expression_attribute_values,
            limit=self._limit,
            exclusive_start_key=start_key,
            index_name=self._index_name,
            consistent_read=self._consistent_read,
            segment=self._segment,
            total_segments=self._total_segments,
        )

        self._current_page = result["items"]
        self._last_evaluated_key = result["last_evaluated_key"]
        self._metrics = result["metrics"]
        self._page_index = 0

        _log_operation(
            "scan",
            self._table,
            self._metrics.duration_ms,
            consumed_rcu=self._metrics.consumed_rcu,
            items_count=self._metrics.items_count,
        )
        if self._metrics.duration_ms > _SLOW_QUERY_THRESHOLD_MS:
            _log_warning("scan", f"slow operation ({self._metrics.duration_ms:.1f}ms)")

        if self._last_evaluated_key is None:
            self._exhausted = True

    async def to_list(self) -> list[dict[str, Any]]:
        """Collect all results into a list."""
        items = []
        async for item in self:
            items.append(item)
        return items
