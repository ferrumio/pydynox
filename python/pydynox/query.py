"""Query result and pagination."""

from typing import TYPE_CHECKING, Any, Callable, Optional

if TYPE_CHECKING:
    from pydynox import pydynox_core


class QueryResult:
    """Result of a DynamoDB query with automatic pagination.

    Iterate over results and access `last_evaluated_key` for manual pagination.

    Example:
        >>> results = client.query("users", key_condition_expression="pk = :pk", ...)
        >>> for item in results:
        ...     print(item["name"])
        >>>
        >>> # Manual pagination if needed
        >>> if results.last_evaluated_key:
        ...     next_page = client.query(..., last_evaluated_key=results.last_evaluated_key)
    """

    def __init__(
        self,
        client: "pydynox_core.DynamoClient",
        table: str,
        key_condition_expression: str,
        filter_expression: Optional[str] = None,
        expression_attribute_names: Optional[dict[str, str]] = None,
        expression_attribute_values: Optional[dict[str, Any]] = None,
        limit: Optional[int] = None,
        scan_index_forward: Optional[bool] = None,
        index_name: Optional[str] = None,
        last_evaluated_key: Optional[dict[str, Any]] = None,
        acquire_rcu: Optional[Callable[[float], None]] = None,
    ):
        self._client = client
        self._table = table
        self._key_condition_expression = key_condition_expression
        self._filter_expression = filter_expression
        self._expression_attribute_names = expression_attribute_names
        self._expression_attribute_values = expression_attribute_values
        self._limit = limit
        self._scan_index_forward = scan_index_forward
        self._index_name = index_name
        self._start_key = last_evaluated_key
        self._acquire_rcu = acquire_rcu

        self._current_page: list[dict[str, Any]] = []
        self._page_index = 0
        self._last_evaluated_key: Optional[dict[str, Any]] = None
        self._exhausted = False
        self._first_fetch = True

    @property
    def last_evaluated_key(self) -> Optional[dict[str, Any]]:
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

        items, self._last_evaluated_key = self._client.query_page(
            self._table,
            self._key_condition_expression,
            filter_expression=self._filter_expression,
            expression_attribute_names=self._expression_attribute_names,
            expression_attribute_values=self._expression_attribute_values,
            limit=self._limit,
            exclusive_start_key=start_key,
            scan_index_forward=self._scan_index_forward,
            index_name=self._index_name,
        )

        self._current_page = items
        self._page_index = 0

        # If no last_key, this is the final page
        if self._last_evaluated_key is None:
            self._exhausted = True
