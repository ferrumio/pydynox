"""Transaction operations for DynamoDB."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pydynox.client import DynamoDBClient


class Transaction:
    """Context manager for transactional write operations.

    Collects put, delete, and update operations, then sends them all
    atomically when the context exits. Either all operations succeed
    or all fail together.

    Example:
        >>> with Transaction(client) as txn:
        ...     txn.put("users", {"pk": "USER#1", "sk": "PROFILE", "name": "Alice"})
        ...     txn.put("users", {"pk": "USER#1", "sk": "SETTINGS", "theme": "dark"})
        ...     txn.delete("users", {"pk": "USER#2", "sk": "PROFILE"})

        >>> # With condition check
        >>> with Transaction(client) as txn:
        ...     txn.condition_check(
        ...         "accounts",
        ...         {"pk": "ACC#1", "sk": "BALANCE"},
        ...         condition_expression="#b >= :amt",
        ...         expression_attribute_names={"#b": "balance"},
        ...         expression_attribute_values={":amt": 100}
        ...     )
        ...     txn.update(
        ...         "accounts",
        ...         {"pk": "ACC#1", "sk": "BALANCE"},
        ...         update_expression="SET #b = #b - :amt",
        ...         expression_attribute_names={"#b": "balance"},
        ...         expression_attribute_values={":amt": 100}
        ...     )
    """

    def __init__(self, client: DynamoDBClient):
        """Create a Transaction.

        Args:
            client: The DynamoDBClient to use.
        """
        self._client = client
        self._operations: list[dict[str, Any]] = []

    def __enter__(self) -> Transaction:
        """Enter the context manager."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit the context manager and execute the transaction."""
        if exc_type is None:
            self.commit()

    def put(
        self,
        table: str,
        item: dict[str, Any],
        condition_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
    ) -> None:
        """Add a put operation to the transaction.

        Args:
            table: The table name.
            item: The item to put (as a dict).
            condition_expression: Optional condition that must be true.
            expression_attribute_names: Optional name placeholders.
            expression_attribute_values: Optional value placeholders.
        """
        op: dict[str, Any] = {
            "type": "put",
            "table": table,
            "item": item,
        }
        if condition_expression:
            op["condition_expression"] = condition_expression
        if expression_attribute_names:
            op["expression_attribute_names"] = expression_attribute_names
        if expression_attribute_values:
            op["expression_attribute_values"] = expression_attribute_values
        self._operations.append(op)

    def delete(
        self,
        table: str,
        key: dict[str, Any],
        condition_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
    ) -> None:
        """Add a delete operation to the transaction.

        Args:
            table: The table name.
            key: The key to delete (as a dict with pk and optional sk).
            condition_expression: Optional condition that must be true.
            expression_attribute_names: Optional name placeholders.
            expression_attribute_values: Optional value placeholders.
        """
        op: dict[str, Any] = {
            "type": "delete",
            "table": table,
            "key": key,
        }
        if condition_expression:
            op["condition_expression"] = condition_expression
        if expression_attribute_names:
            op["expression_attribute_names"] = expression_attribute_names
        if expression_attribute_values:
            op["expression_attribute_values"] = expression_attribute_values
        self._operations.append(op)

    def update(
        self,
        table: str,
        key: dict[str, Any],
        update_expression: str,
        condition_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
    ) -> None:
        """Add an update operation to the transaction.

        Args:
            table: The table name.
            key: The key to update (as a dict with pk and optional sk).
            update_expression: The update expression (e.g., "SET #n = :v").
            condition_expression: Optional condition that must be true.
            expression_attribute_names: Optional name placeholders.
            expression_attribute_values: Optional value placeholders.
        """
        op: dict[str, Any] = {
            "type": "update",
            "table": table,
            "key": key,
            "update_expression": update_expression,
        }
        if condition_expression:
            op["condition_expression"] = condition_expression
        if expression_attribute_names:
            op["expression_attribute_names"] = expression_attribute_names
        if expression_attribute_values:
            op["expression_attribute_values"] = expression_attribute_values
        self._operations.append(op)

    def condition_check(
        self,
        table: str,
        key: dict[str, Any],
        condition_expression: str,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
    ) -> None:
        """Add a condition check to the transaction.

        A condition check verifies that a condition is true without
        modifying the item. If the condition fails, the whole transaction
        is rolled back.

        Args:
            table: The table name.
            key: The key to check (as a dict with pk and optional sk).
            condition_expression: The condition that must be true.
            expression_attribute_names: Optional name placeholders.
            expression_attribute_values: Optional value placeholders.
        """
        op: dict[str, Any] = {
            "type": "condition_check",
            "table": table,
            "key": key,
            "condition_expression": condition_expression,
        }
        if expression_attribute_names:
            op["expression_attribute_names"] = expression_attribute_names
        if expression_attribute_values:
            op["expression_attribute_values"] = expression_attribute_values
        self._operations.append(op)

    def commit(self) -> None:
        """Execute all collected operations atomically.

        Called automatically when exiting the context manager.
        Can also be called manually to execute operations early.

        Raises:
            ValueError: If a condition check fails or validation error occurs.
            RuntimeError: If the transaction fails for other reasons.
        """
        if not self._operations:
            return

        self._client.transact_write(self._operations)

        # Clear operations after successful commit
        self._operations = []


class AsyncTransaction:
    """Async context manager for transactional write operations.

    Same as Transaction but for async code.

    Example:
        >>> async with AsyncTransaction(client) as txn:
        ...     txn.put("users", {"pk": "USER#1", "sk": "PROFILE", "name": "Alice"})
        ...     txn.delete("users", {"pk": "USER#2", "sk": "PROFILE"})
    """

    def __init__(self, client: DynamoDBClient):
        """Create an AsyncTransaction.

        Args:
            client: The DynamoDBClient to use.
        """
        self._client = client
        self._operations: list[dict[str, Any]] = []

    async def __aenter__(self) -> AsyncTransaction:
        """Enter the async context manager."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit the async context manager and execute the transaction."""
        if exc_type is None:
            await self.commit()

    def put(
        self,
        table: str,
        item: dict[str, Any],
        condition_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
    ) -> None:
        """Add a put operation to the transaction."""
        op: dict[str, Any] = {
            "type": "put",
            "table": table,
            "item": item,
        }
        if condition_expression:
            op["condition_expression"] = condition_expression
        if expression_attribute_names:
            op["expression_attribute_names"] = expression_attribute_names
        if expression_attribute_values:
            op["expression_attribute_values"] = expression_attribute_values
        self._operations.append(op)

    def delete(
        self,
        table: str,
        key: dict[str, Any],
        condition_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
    ) -> None:
        """Add a delete operation to the transaction."""
        op: dict[str, Any] = {
            "type": "delete",
            "table": table,
            "key": key,
        }
        if condition_expression:
            op["condition_expression"] = condition_expression
        if expression_attribute_names:
            op["expression_attribute_names"] = expression_attribute_names
        if expression_attribute_values:
            op["expression_attribute_values"] = expression_attribute_values
        self._operations.append(op)

    def update(
        self,
        table: str,
        key: dict[str, Any],
        update_expression: str,
        condition_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
    ) -> None:
        """Add an update operation to the transaction."""
        op: dict[str, Any] = {
            "type": "update",
            "table": table,
            "key": key,
            "update_expression": update_expression,
        }
        if condition_expression:
            op["condition_expression"] = condition_expression
        if expression_attribute_names:
            op["expression_attribute_names"] = expression_attribute_names
        if expression_attribute_values:
            op["expression_attribute_values"] = expression_attribute_values
        self._operations.append(op)

    def condition_check(
        self,
        table: str,
        key: dict[str, Any],
        condition_expression: str,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
    ) -> None:
        """Add a condition check to the transaction."""
        op: dict[str, Any] = {
            "type": "condition_check",
            "table": table,
            "key": key,
            "condition_expression": condition_expression,
        }
        if expression_attribute_names:
            op["expression_attribute_names"] = expression_attribute_names
        if expression_attribute_values:
            op["expression_attribute_values"] = expression_attribute_values
        self._operations.append(op)

    async def commit(self) -> None:
        """Execute all collected operations atomically.

        Called automatically when exiting the async context manager.
        Can also be called manually to execute operations early.
        """
        if not self._operations:
            return

        await self._client.async_transact_write(self._operations)

        # Clear operations after successful commit
        self._operations = []
