"""DynamoDB client wrapper."""

from typing import Any, Optional

from .query import QueryResult


class DynamoClient:
    """DynamoDB client with flexible credential configuration.

    Supports multiple credential sources in order of priority:
    1. Hardcoded credentials (access_key, secret_key, session_token)
    2. AWS profile from ~/.aws/credentials
    3. Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
    4. Default credential chain (instance profile, etc.)

    Example:
        >>> # Use environment variables
        >>> client = DynamoClient()

        >>> # Use hardcoded credentials
        >>> client = DynamoClient(
        ...     access_key="AKIA...",
        ...     secret_key="secret...",
        ...     region="us-east-1"
        ... )

        >>> # Use AWS profile
        >>> client = DynamoClient(profile="my-profile")

        >>> # Use local endpoint (localstack, moto)
        >>> client = DynamoClient(endpoint_url="http://localhost:4566")
    """

    def __init__(
        self,
        region: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        session_token: Optional[str] = None,
        profile: Optional[str] = None,
        endpoint_url: Optional[str] = None,
    ):
        from pydynox import pydynox_core

        self._client = pydynox_core.DynamoClient(
            region=region,
            access_key=access_key,
            secret_key=secret_key,
            session_token=session_token,
            profile=profile,
            endpoint_url=endpoint_url,
        )

    def get_region(self) -> str:
        """Get the configured AWS region."""
        return self._client.get_region()

    def ping(self) -> bool:
        """Check if the client can connect to DynamoDB."""
        return self._client.ping()

    def put_item(self, table: str, item: dict[str, Any]) -> None:
        """Put an item into a DynamoDB table.

        Args:
            table: The name of the DynamoDB table.
            item: A dict representing the item to save.

        Example:
            >>> client.put_item("users", {"pk": "USER#123", "name": "John", "age": 30})
        """
        self._client.put_item(table, item)

    def get_item(self, table: str, key: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Get an item from a DynamoDB table by its key.

        Args:
            table: The name of the DynamoDB table.
            key: A dict with the key attributes (hash key and optional range key).

        Returns:
            The item as a dict if found, None if not found.

        Example:
            >>> item = client.get_item("users", {"pk": "USER#123"})
            >>> if item:
            ...     print(item["name"])
        """
        return self._client.get_item(table, key)

    def delete_item(
        self,
        table: str,
        key: dict[str, Any],
        condition_expression: Optional[str] = None,
        expression_attribute_names: Optional[dict[str, str]] = None,
        expression_attribute_values: Optional[dict[str, Any]] = None,
    ) -> None:
        """Delete an item from a DynamoDB table.

        Args:
            table: The name of the DynamoDB table.
            key: A dict with the key attributes.
            condition_expression: Optional condition expression.
            expression_attribute_names: Optional name placeholders.
            expression_attribute_values: Optional value placeholders.

        Example:
            >>> client.delete_item("users", {"pk": "USER#123"})
        """
        self._client.delete_item(
            table,
            key,
            condition_expression=condition_expression,
            expression_attribute_names=expression_attribute_names,
            expression_attribute_values=expression_attribute_values,
        )

    def update_item(
        self,
        table: str,
        key: dict[str, Any],
        updates: Optional[dict[str, Any]] = None,
        update_expression: Optional[str] = None,
        condition_expression: Optional[str] = None,
        expression_attribute_names: Optional[dict[str, str]] = None,
        expression_attribute_values: Optional[dict[str, Any]] = None,
    ) -> None:
        """Update an item in a DynamoDB table.

        Args:
            table: The name of the DynamoDB table.
            key: A dict with the key attributes.
            updates: Optional dict of field:value pairs for simple SET updates.
            update_expression: Optional full update expression string.
            condition_expression: Optional condition expression.
            expression_attribute_names: Optional name placeholders.
            expression_attribute_values: Optional value placeholders.

        Example:
            >>> # Simple update
            >>> client.update_item("users", {"pk": "USER#123"}, updates={"name": "John"})

            >>> # Atomic increment
            >>> client.update_item(
            ...     "users",
            ...     {"pk": "USER#123"},
            ...     update_expression="SET #c = #c + :val",
            ...     expression_attribute_names={"#c": "counter"},
            ...     expression_attribute_values={":val": 1}
            ... )
        """
        self._client.update_item(
            table,
            key,
            updates=updates,
            update_expression=update_expression,
            condition_expression=condition_expression,
            expression_attribute_names=expression_attribute_names,
            expression_attribute_values=expression_attribute_values,
        )

    def query(
        self,
        table: str,
        key_condition_expression: str,
        filter_expression: Optional[str] = None,
        expression_attribute_names: Optional[dict[str, str]] = None,
        expression_attribute_values: Optional[dict[str, Any]] = None,
        limit: Optional[int] = None,
        scan_index_forward: Optional[bool] = None,
        index_name: Optional[str] = None,
        last_evaluated_key: Optional[dict[str, Any]] = None,
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
        )

    def batch_write(
        self,
        table: str,
        put_items: Optional[list[dict[str, Any]]] = None,
        delete_keys: Optional[list[dict[str, Any]]] = None,
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
            ...     {"type": "put", "table": "orders", "item": {"pk": "ORD#1", "sk": "INFO", "status": "new"}},
            ...     {"type": "put", "table": "orders", "item": {"pk": "ORD#1", "sk": "ITEM#1", "product": "Widget"}}
            ... ])
        """
        self._client.transact_write(operations)
