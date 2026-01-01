"""DynamoDB client wrapper."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydynox._internal._logging import _log_operation, _log_warning
from pydynox._internal._metrics import DictWithMetrics, OperationMetrics
from pydynox.query import AsyncQueryResult, QueryResult

if TYPE_CHECKING:
    from pydynox.rate_limit import AdaptiveRate, FixedRate

# Threshold for slow query warning (ms)
_SLOW_QUERY_THRESHOLD_MS = 100.0


class DynamoDBClient:
    """DynamoDB client with flexible credential configuration.

    Supports multiple credential sources in order of priority:
    1. Hardcoded credentials (access_key, secret_key, session_token)
    2. AWS profile from ~/.aws/credentials
    3. Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
    4. Default credential chain (instance profile, etc.)

    Example:
        >>> # Use environment variables
        >>> client = DynamoDBClient()

        >>> # Use hardcoded credentials
        >>> client = DynamoDBClient(
        ...     access_key="AKIA...",
        ...     secret_key="secret...",
        ...     region="us-east-1"
        ... )

        >>> # Use AWS profile
        >>> client = DynamoDBClient(profile="my-profile")

        >>> # Use local endpoint (localstack, moto)
        >>> client = DynamoDBClient(endpoint_url="http://localhost:4566")

        >>> # With rate limiting
        >>> from pydynox import FixedRate, AdaptiveRate
        >>> client = DynamoDBClient(rate_limit=FixedRate(rcu=50))
        >>> client = DynamoDBClient(rate_limit=AdaptiveRate(max_rcu=100))
    """

    def __init__(
        self,
        region: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        session_token: str | None = None,
        profile: str | None = None,
        endpoint_url: str | None = None,
        rate_limit: FixedRate | AdaptiveRate | None = None,
    ):
        from pydynox import pydynox_core

        self._client = pydynox_core.DynamoDBClient(
            region=region,
            access_key=access_key,
            secret_key=secret_key,
            session_token=session_token,
            profile=profile,
            endpoint_url=endpoint_url,
        )
        self._rate_limit = rate_limit

    @property
    def rate_limit(self) -> FixedRate | AdaptiveRate | None:
        """Get the rate limiter for this client."""
        return self._rate_limit

    def _acquire_rcu(self, rcu: float = 1.0) -> None:
        """Acquire read capacity before an operation."""
        if self._rate_limit is not None:
            self._rate_limit._acquire_rcu(rcu)

    def _acquire_wcu(self, wcu: float = 1.0) -> None:
        """Acquire write capacity before an operation."""
        if self._rate_limit is not None:
            self._rate_limit._acquire_wcu(wcu)

    def _on_throttle(self) -> None:
        """Record a throttle event."""
        if self._rate_limit is not None:
            self._rate_limit._on_throttle()

    def get_region(self) -> str:
        """Get the configured AWS region."""
        return self._client.get_region()

    def ping(self) -> bool:
        """Check if the client can connect to DynamoDB."""
        return self._client.ping()

    def put_item(
        self,
        table: str,
        item: dict[str, Any],
        condition_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
    ) -> OperationMetrics:
        """Put an item into a DynamoDB table.

        Args:
            table: The name of the DynamoDB table.
            item: A dict representing the item to save.
            condition_expression: Optional condition expression.
            expression_attribute_names: Optional name placeholders.
            expression_attribute_values: Optional value placeholders.

        Returns:
            OperationMetrics with timing and capacity info.

        Example:
            >>> metrics = client.put_item("users", {"pk": "USER#123", "name": "John"})
            >>> print(metrics.duration_ms)
            >>> print(metrics.consumed_wcu)
        """
        self._acquire_wcu(1.0)
        metrics = self._client.put_item(
            table,
            item,
            condition_expression=condition_expression,
            expression_attribute_names=expression_attribute_names,
            expression_attribute_values=expression_attribute_values,
        )
        _log_operation(
            "put_item",
            table,
            metrics.duration_ms,
            consumed_wcu=metrics.consumed_wcu,
        )
        if metrics.duration_ms > _SLOW_QUERY_THRESHOLD_MS:
            _log_warning("put_item", f"slow operation ({metrics.duration_ms:.1f}ms)")
        return metrics

    def get_item(self, table: str, key: dict[str, Any]) -> DictWithMetrics | None:
        """Get an item from a DynamoDB table by its key.

        Args:
            table: The name of the DynamoDB table.
            key: A dict with the key attributes (hash key and optional range key).

        Returns:
            The item as a DictWithMetrics if found (with .metrics), None if not found.

        Example:
            >>> item = client.get_item("users", {"pk": "USER#123"})
            >>> if item:
            ...     print(item["name"])
            ...     print(item.metrics.duration_ms)
        """
        self._acquire_rcu(1.0)
        result, metrics = self._client.get_item(table, key)
        _log_operation(
            "get_item",
            table,
            metrics.duration_ms,
            consumed_rcu=metrics.consumed_rcu,
        )
        if metrics.duration_ms > _SLOW_QUERY_THRESHOLD_MS:
            _log_warning("get_item", f"slow operation ({metrics.duration_ms:.1f}ms)")
        if result is None:
            return None
        return DictWithMetrics(result, metrics)

    def delete_item(
        self,
        table: str,
        key: dict[str, Any],
        condition_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
    ) -> OperationMetrics:
        """Delete an item from a DynamoDB table.

        Args:
            table: The name of the DynamoDB table.
            key: A dict with the key attributes.
            condition_expression: Optional condition expression.
            expression_attribute_names: Optional name placeholders.
            expression_attribute_values: Optional value placeholders.

        Returns:
            OperationMetrics with timing and capacity info.

        Example:
            >>> metrics = client.delete_item("users", {"pk": "USER#123"})
            >>> print(metrics.duration_ms)
        """
        self._acquire_wcu(1.0)
        metrics = self._client.delete_item(
            table,
            key,
            condition_expression=condition_expression,
            expression_attribute_names=expression_attribute_names,
            expression_attribute_values=expression_attribute_values,
        )
        _log_operation(
            "delete_item",
            table,
            metrics.duration_ms,
            consumed_wcu=metrics.consumed_wcu,
        )
        if metrics.duration_ms > _SLOW_QUERY_THRESHOLD_MS:
            _log_warning("delete_item", f"slow operation ({metrics.duration_ms:.1f}ms)")
        return metrics

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
        """Update an item in a DynamoDB table.

        Args:
            table: The name of the DynamoDB table.
            key: A dict with the key attributes.
            updates: Optional dict of field:value pairs for simple SET updates.
            update_expression: Optional full update expression string.
            condition_expression: Optional condition expression.
            expression_attribute_names: Optional name placeholders.
            expression_attribute_values: Optional value placeholders.

        Returns:
            OperationMetrics with timing and capacity info.

        Example:
            >>> metrics = client.update_item("users", {"pk": "USER#123"}, updates={"name": "John"})
            >>> print(metrics.duration_ms)
        """
        self._acquire_wcu(1.0)
        metrics = self._client.update_item(
            table,
            key,
            updates=updates,
            update_expression=update_expression,
            condition_expression=condition_expression,
            expression_attribute_names=expression_attribute_names,
            expression_attribute_values=expression_attribute_values,
        )
        _log_operation(
            "update_item",
            table,
            metrics.duration_ms,
            consumed_wcu=metrics.consumed_wcu,
        )
        if metrics.duration_ms > _SLOW_QUERY_THRESHOLD_MS:
            _log_warning("update_item", f"slow operation ({metrics.duration_ms:.1f}ms)")
        return metrics

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
    ) -> QueryResult:
        """Query items from a DynamoDB table.

        Returns an iterable result with automatic pagination.
        Access `last_evaluated_key` for manual pagination control.

        Args:
            table: The name of the DynamoDB table.
            key_condition_expression: Key condition (e.g., "pk = :pk").
            filter_expression: Optional filter for non-key attributes.
            expression_attribute_names: Name placeholders (e.g., {"#pk": "pk"}).
            expression_attribute_values: Value placeholders (e.g., {":pk": "USER#123"}).
            limit: Optional max items per page (not total).
            scan_index_forward: Sort order (True = ascending, False = descending).
            index_name: Optional GSI or LSI name.
            last_evaluated_key: Start key for pagination (from previous query).

        Returns:
            A QueryResult that can be iterated and has `last_evaluated_key`.

        Example:
            >>> # Simple iteration
            >>> for item in client.query("users", key_condition_expression="pk = :pk", ...):
            ...     print(item["name"])

            >>> # Manual pagination
            >>> results = client.query("users", ..., limit=10)
            >>> for item in results:
            ...     process(item)
            >>> if results.last_evaluated_key:
            ...     next_page = client.query(..., last_evaluated_key=results.last_evaluated_key)
        """
        return QueryResult(
            self._client,
            table,
            key_condition_expression,
            filter_expression=filter_expression,
            expression_attribute_names=expression_attribute_names,
            expression_attribute_values=expression_attribute_values,
            limit=limit,
            scan_index_forward=scan_index_forward,
            index_name=index_name,
            last_evaluated_key=last_evaluated_key,
            acquire_rcu=self._acquire_rcu,
        )

    def batch_write(
        self,
        table: str,
        put_items: list[dict[str, Any]] | None = None,
        delete_keys: list[dict[str, Any]] | None = None,
    ) -> None:
        """Batch write items to a DynamoDB table.

        Writes multiple items in a single request. Handles:
        - Splitting requests to respect the 25-item limit per batch
        - Retrying unprocessed items with exponential backoff

        Args:
            table: The name of the DynamoDB table.
            put_items: List of items to put (as dicts).
            delete_keys: List of keys to delete (as dicts).

        Example:
            >>> # Batch put items
            >>> client.batch_write(
            ...     "users",
            ...     put_items=[
            ...         {"pk": "USER#1", "sk": "PROFILE", "name": "Alice"},
            ...         {"pk": "USER#2", "sk": "PROFILE", "name": "Bob"},
            ...     ]
            ... )

            >>> # Batch delete items
            >>> client.batch_write(
            ...     "users",
            ...     delete_keys=[
            ...         {"pk": "USER#3", "sk": "PROFILE"},
            ...         {"pk": "USER#4", "sk": "PROFILE"},
            ...     ]
            ... )
        """
        put_count = len(put_items) if put_items else 0
        delete_count = len(delete_keys) if delete_keys else 0
        self._acquire_wcu(float(put_count + delete_count))
        self._client.batch_write(
            table,
            put_items or [],
            delete_keys or [],
        )

    def batch_get(
        self,
        table: str,
        keys: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Batch get items from a DynamoDB table.

        Gets multiple items in a single request. Handles:
        - Splitting requests to respect the 100-item limit per batch
        - Retrying unprocessed keys with exponential backoff
        - Combining results from multiple requests

        Args:
            table: The name of the DynamoDB table.
            keys: List of keys to get (as dicts with hash key and optional range key).

        Returns:
            List of items that were found (as dicts). Items not found are not
            included in the result. The order of items may not match the order
            of keys.

        Example:
            >>> # Batch get items
            >>> keys = [
            ...     {"pk": "USER#1", "sk": "PROFILE"},
            ...     {"pk": "USER#2", "sk": "PROFILE"},
            ...     {"pk": "USER#3", "sk": "PROFILE"},
            ... ]
            >>> items = client.batch_get("users", keys)
            >>> for item in items:
            ...     print(item["name"])
        """
        self._acquire_rcu(float(len(keys)))
        return self._client.batch_get(table, keys)

    def transact_write(self, operations: list[dict[str, Any]]) -> None:
        """Execute a transactional write operation.

        All operations run atomically. Either all succeed or all fail.
        Use this when you need data consistency across multiple items.

        Args:
            operations: List of operation dicts, each with:
                - type: "put", "delete", "update", or "condition_check"
                - table: Table name
                - item: Item to put (for "put" type)
                - key: Key dict (for "delete", "update", "condition_check")
                - update_expression: Update expression (for "update" type)
                - condition_expression: Optional condition expression
                - expression_attribute_names: Optional name placeholders
                - expression_attribute_values: Optional value placeholders

        Raises:
            ValueError: If a condition check fails or validation error occurs.
            RuntimeError: If the transaction fails for other reasons.

        Example:
            >>> # Transfer money between accounts atomically
            >>> client.transact_write([
            ...     {
            ...         "type": "update",
            ...         "table": "accounts",
            ...         "key": {"pk": "ACC#1", "sk": "BALANCE"},
            ...         "update_expression": "SET #b = #b - :amt",
            ...         "condition_expression": "#b >= :amt",
            ...         "expression_attribute_names": {"#b": "balance"},
            ...         "expression_attribute_values": {":amt": 100}
            ...     },
            ...     {
            ...         "type": "update",
            ...         "table": "accounts",
            ...         "key": {"pk": "ACC#2", "sk": "BALANCE"},
            ...         "update_expression": "SET #b = #b + :amt",
            ...         "expression_attribute_names": {"#b": "balance"},
            ...         "expression_attribute_values": {":amt": 100}
            ...     }
            ... ])

            >>> # Put multiple items atomically
            >>> client.transact_write([
            ...     {"type": "put", "table": "orders",
            ...      "item": {"pk": "ORD#1", "sk": "INFO", "status": "new"}},
            ...     {"type": "put", "table": "orders",
            ...      "item": {"pk": "ORD#1", "sk": "ITEM#1", "product": "Widget"}}
            ... ])
        """
        self._client.transact_write(operations)

    def create_table(
        self,
        table_name: str,
        hash_key: tuple[str, str],
        range_key: tuple[str, str] | None = None,
        billing_mode: str = "PAY_PER_REQUEST",
        read_capacity: int | None = None,
        write_capacity: int | None = None,
        table_class: str | None = None,
        encryption: str | None = None,
        kms_key_id: str | None = None,
        global_secondary_indexes: list[dict[str, Any]] | None = None,
        wait: bool = False,
    ) -> None:
        """Create a new DynamoDB table.

        Useful for local development and testing with moto/localstack.
        For production, use CDK, CloudFormation, or Terraform instead.

        Args:
            table_name: Name of the table to create.
            hash_key: Tuple of (attribute_name, attribute_type) for the hash key.
                      Type can be "S" (string), "N" (number), or "B" (binary).
            range_key: Optional tuple of (attribute_name, attribute_type) for the range key.
            billing_mode: "PAY_PER_REQUEST" (default) or "PROVISIONED".
            read_capacity: Read capacity units (only for PROVISIONED, default: 5).
            write_capacity: Write capacity units (only for PROVISIONED, default: 5).
            table_class: "STANDARD" (default) or "STANDARD_INFREQUENT_ACCESS".
            encryption: "AWS_OWNED" (default), "AWS_MANAGED", or "CUSTOMER_MANAGED".
            kms_key_id: KMS key ARN (required when encryption is "CUSTOMER_MANAGED").
            global_secondary_indexes: Optional list of GSI definitions. Each GSI is a dict:
                - index_name: Name of the GSI
                - hash_key: Tuple of (attribute_name, attribute_type)
                - range_key: Optional tuple of (attribute_name, attribute_type)
                - projection: "ALL" (default), "KEYS_ONLY", or "INCLUDE"
                - non_key_attributes: List of attribute names (required for "INCLUDE")
            wait: If True, wait for table to become ACTIVE before returning.

        Example:
            >>> # Create table with on-demand billing
            >>> client.create_table(
            ...     "users",
            ...     hash_key=("pk", "S"),
            ...     range_key=("sk", "S")
            ... )

            >>> # Create table with GSI
            >>> client.create_table(
            ...     "users",
            ...     hash_key=("pk", "S"),
            ...     range_key=("sk", "S"),
            ...     global_secondary_indexes=[
            ...         {
            ...             "index_name": "email-index",
            ...             "hash_key": ("email", "S"),
            ...             "projection": "ALL",
            ...         }
            ...     ]
            ... )

            >>> # Create table with customer managed KMS encryption
            >>> client.create_table(
            ...     "orders",
            ...     hash_key=("pk", "S"),
            ...     encryption="CUSTOMER_MANAGED",
            ...     kms_key_id="arn:aws:kms:us-east-1:123456789:key/abc-123",
            ...     wait=True
            ... )
        """
        self._client.create_table(
            table_name,
            hash_key,
            range_key=range_key,
            billing_mode=billing_mode,
            read_capacity=read_capacity,
            write_capacity=write_capacity,
            table_class=table_class,
            encryption=encryption,
            kms_key_id=kms_key_id,
            global_secondary_indexes=global_secondary_indexes,
            wait=wait,
        )

    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists.

        Args:
            table_name: Name of the table to check.

        Returns:
            True if the table exists, False otherwise.

        Example:
            >>> if not client.table_exists("users"):
            ...     client.create_table("users", hash_key=("pk", "S"))
        """
        return self._client.table_exists(table_name)

    def delete_table(self, table_name: str) -> None:
        """Delete a table.

        Args:
            table_name: Name of the table to delete.

        Example:
            >>> client.delete_table("users")
        """
        self._client.delete_table(table_name)

    def wait_for_table_active(
        self,
        table_name: str,
        timeout_seconds: int | None = None,
    ) -> None:
        """Wait for a table to become active.

        Polls the table status until it becomes ACTIVE or times out.

        Args:
            table_name: Name of the table to wait for.
            timeout_seconds: Maximum time to wait (default: 60).

        Raises:
            TimeoutError: If the table doesn't become active within the timeout.

        Example:
            >>> client.create_table("users", hash_key=("pk", "S"))
            >>> client.wait_for_table_active("users", timeout_seconds=30)
        """
        self._client.wait_for_table_active(table_name, timeout_seconds=timeout_seconds)

    # ========== ASYNC METHODS ==========

    async def async_get_item(self, table: str, key: dict[str, Any]) -> DictWithMetrics | None:
        """Async version of get_item.

        Args:
            table: The name of the DynamoDB table.
            key: A dict with the key attributes.

        Returns:
            The item as a DictWithMetrics if found, None if not found.

        Example:
            >>> item = await client.async_get_item("users", {"pk": "USER#123"})
            >>> if item:
            ...     print(item["name"])
        """
        self._acquire_rcu(1.0)
        result = await self._client.async_get_item(table, key)
        metrics = result["metrics"]
        _log_operation("get_item", table, metrics.duration_ms, consumed_rcu=metrics.consumed_rcu)
        if metrics.duration_ms > _SLOW_QUERY_THRESHOLD_MS:
            _log_warning("get_item", f"slow operation ({metrics.duration_ms:.1f}ms)")
        if result["item"] is None:
            return None
        return DictWithMetrics(result["item"], metrics)

    async def async_put_item(
        self,
        table: str,
        item: dict[str, Any],
        condition_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
    ) -> OperationMetrics:
        """Async version of put_item.

        Args:
            table: The name of the DynamoDB table.
            item: A dict representing the item to save.
            condition_expression: Optional condition expression.
            expression_attribute_names: Optional name placeholders.
            expression_attribute_values: Optional value placeholders.

        Returns:
            OperationMetrics with timing and capacity info.

        Example:
            >>> metrics = await client.async_put_item("users", {"pk": "USER#123", "name": "John"})
        """
        self._acquire_wcu(1.0)
        metrics = await self._client.async_put_item(
            table,
            item,
            condition_expression=condition_expression,
            expression_attribute_names=expression_attribute_names,
            expression_attribute_values=expression_attribute_values,
        )
        _log_operation("put_item", table, metrics.duration_ms, consumed_wcu=metrics.consumed_wcu)
        if metrics.duration_ms > _SLOW_QUERY_THRESHOLD_MS:
            _log_warning("put_item", f"slow operation ({metrics.duration_ms:.1f}ms)")
        return metrics

    async def async_delete_item(
        self,
        table: str,
        key: dict[str, Any],
        condition_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
    ) -> OperationMetrics:
        """Async version of delete_item.

        Args:
            table: The name of the DynamoDB table.
            key: A dict with the key attributes.
            condition_expression: Optional condition expression.
            expression_attribute_names: Optional name placeholders.
            expression_attribute_values: Optional value placeholders.

        Returns:
            OperationMetrics with timing and capacity info.

        Example:
            >>> metrics = await client.async_delete_item("users", {"pk": "USER#123"})
        """
        self._acquire_wcu(1.0)
        metrics = await self._client.async_delete_item(
            table,
            key,
            condition_expression=condition_expression,
            expression_attribute_names=expression_attribute_names,
            expression_attribute_values=expression_attribute_values,
        )
        _log_operation("delete_item", table, metrics.duration_ms, consumed_wcu=metrics.consumed_wcu)
        if metrics.duration_ms > _SLOW_QUERY_THRESHOLD_MS:
            _log_warning("delete_item", f"slow operation ({metrics.duration_ms:.1f}ms)")
        return metrics

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
        """Async version of update_item.

        Args:
            table: The name of the DynamoDB table.
            key: A dict with the key attributes.
            updates: Optional dict of field:value pairs for simple SET updates.
            update_expression: Optional full update expression string.
            condition_expression: Optional condition expression.
            expression_attribute_names: Optional name placeholders.
            expression_attribute_values: Optional value placeholders.

        Returns:
            OperationMetrics with timing and capacity info.

        Example:
            >>> metrics = await client.async_update_item(
            ...     "users", {"pk": "USER#123"}, updates={"name": "John"}
            ... )
        """
        self._acquire_wcu(1.0)
        metrics = await self._client.async_update_item(
            table,
            key,
            updates=updates,
            update_expression=update_expression,
            condition_expression=condition_expression,
            expression_attribute_names=expression_attribute_names,
            expression_attribute_values=expression_attribute_values,
        )
        _log_operation("update_item", table, metrics.duration_ms, consumed_wcu=metrics.consumed_wcu)
        if metrics.duration_ms > _SLOW_QUERY_THRESHOLD_MS:
            _log_warning("update_item", f"slow operation ({metrics.duration_ms:.1f}ms)")
        return metrics

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
    ) -> "AsyncQueryResult":
        """Async query items from a DynamoDB table.

        Returns an async iterable result with automatic pagination.

        Args:
            table: The name of the DynamoDB table.
            key_condition_expression: Key condition (e.g., "pk = :pk").
            filter_expression: Optional filter for non-key attributes.
            expression_attribute_names: Name placeholders.
            expression_attribute_values: Value placeholders.
            limit: Optional max items per page.
            scan_index_forward: Sort order (True = ascending).
            index_name: Optional GSI or LSI name.
            last_evaluated_key: Start key for pagination.

        Returns:
            An AsyncQueryResult that can be async iterated.

        Example:
            >>> async for item in client.async_query("users", ...):
            ...     print(item["name"])
        """
        return AsyncQueryResult(
            self._client,
            table,
            key_condition_expression,
            filter_expression=filter_expression,
            expression_attribute_names=expression_attribute_names,
            expression_attribute_values=expression_attribute_values,
            limit=limit,
            scan_index_forward=scan_index_forward,
            index_name=index_name,
            last_evaluated_key=last_evaluated_key,
            acquire_rcu=self._acquire_rcu,
        )
