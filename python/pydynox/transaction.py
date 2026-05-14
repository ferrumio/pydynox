"""Transaction operations for DynamoDB."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydynox._internal._logging import _log_debug

if TYPE_CHECKING:
    from pydynox.client import DynamoDBClient
    from pydynox.model import Model


class Transaction:
    """Async context manager for transactional write operations.

    Collects put, delete, and update operations, then sends them all
    atomically when the context exits. Either all operations succeed
    or all fail together.

    Example:
        >>> async with Transaction(client) as txn:
        ...     txn.put("users", {"pk": "USER#1", "sk": "PROFILE", "name": "Alice"})
        ...     txn.put("users", {"pk": "USER#1", "sk": "SETTINGS", "theme": "dark"})
        ...     txn.delete("users", {"pk": "USER#2", "sk": "PROFILE"})

        >>> # With condition check
        >>> async with Transaction(client) as txn:
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
        self._models: list[tuple[Model, str | None, int]] = []

    async def __aenter__(self) -> Transaction:
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

    def save_model(self, model: Model, condition: Any | None = None) -> None:
        """Add a model save to the transaction.

        Handles version attribute automatically. After commit, the model's
        version is updated and change tracking is reset.

        Args:
            model: The model instance to save.
            condition: Optional additional condition.
        """
        _prepare_model_save(self, model, condition)

    def delete_model(self, model: Model, condition: Any | None = None) -> None:
        """Add a model delete to the transaction.

        Handles version condition automatically.

        Args:
            model: The model instance to delete.
            condition: Optional additional condition.
        """
        _prepare_model_delete(self, model, condition)

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

    async def commit(self) -> None:
        """Execute all collected operations atomically.

        Called automatically when exiting the async context manager.
        Can also be called manually to execute operations early.

        Raises:
            ValueError: If a condition check fails or validation error occurs.
            RuntimeError: If the transaction fails for other reasons.
        """
        if not self._operations:
            return

        _log_debug("transaction", f"Committing transaction ({len(self._operations)} operations)")
        await self._client.transact_write(self._operations)

        _finalize_models(self._models)
        self._operations = []
        self._models = []


class SyncTransaction:
    """Sync context manager for transactional write operations.

    Same as Transaction but for sync code.

    Example:
        >>> with SyncTransaction(client) as txn:
        ...     txn.put("users", {"pk": "USER#1", "sk": "PROFILE", "name": "Alice"})
        ...     txn.delete("users", {"pk": "USER#2", "sk": "PROFILE"})
    """

    def __init__(self, client: DynamoDBClient):
        """Create a SyncTransaction.

        Args:
            client: The DynamoDBClient to use.
        """
        self._client = client
        self._operations: list[dict[str, Any]] = []
        self._models: list[tuple[Model, str | None, int]] = []

    def __enter__(self) -> SyncTransaction:
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

    def save_model(self, model: Model, condition: Any | None = None) -> None:
        """Add a model save to the transaction.

        Handles version attribute automatically. After commit, the model's
        version is updated and change tracking is reset.

        Args:
            model: The model instance to save.
            condition: Optional additional condition.
        """
        _prepare_model_save(self, model, condition)

    def delete_model(self, model: Model, condition: Any | None = None) -> None:
        """Add a model delete to the transaction.

        Handles version condition automatically.

        Args:
            model: The model instance to delete.
            condition: Optional additional condition.
        """
        _prepare_model_delete(self, model, condition)

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

    def commit(self) -> None:
        """Execute all collected operations atomically.

        Called automatically when exiting the context manager.
        Can also be called manually to execute operations early.
        """
        if not self._operations:
            return

        _log_debug("transaction", f"Committing transaction ({len(self._operations)} operations)")
        self._client.sync_transact_write(self._operations)

        _finalize_models(self._models)
        self._operations = []
        self._models = []


def _prepare_model_save(
    txn: Transaction | SyncTransaction,
    model: Model,
    condition: Any | None,
) -> None:
    """Build a put operation from a model and track it for post-commit updates."""
    from pydynox.hooks import HookType

    model._run_hooks(HookType.BEFORE_SAVE)
    model._apply_auto_generate()

    version_attr = model._get_version_attr_name()
    version_condition, new_version = model._build_version_condition()

    final_condition = condition
    if version_condition is not None:
        final_condition = (
            final_condition & version_condition if final_condition else version_condition
        )

    if version_attr is not None:
        setattr(model, version_attr, new_version)

    table = model._get_table()
    item = model.to_dict()

    op: dict[str, Any] = {"type": "put", "table": table, "item": item}

    if final_condition is not None:
        names: dict[str, str] = {}
        values: dict[str, Any] = {}
        expr = final_condition.serialize(names, values)
        op["condition_expression"] = expr
        op["expression_attribute_names"] = {v: k for k, v in names.items()}
        op["expression_attribute_values"] = values

    txn._operations.append(op)
    txn._models.append((model, version_attr, new_version))


def _prepare_model_delete(
    txn: Transaction | SyncTransaction,
    model: Model,
    condition: Any | None,
) -> None:
    """Build a delete operation from a model and track it."""
    from pydynox._internal._conditions import ConditionPath
    from pydynox.hooks import HookType

    model._run_hooks(HookType.BEFORE_DELETE)

    version_attr = model._get_version_attr_name()
    version_condition = None
    if version_attr is not None:
        current_version: int | None = getattr(model, version_attr, None)
        if current_version is not None:
            dynamo_name = model._py_to_dynamo.get(version_attr, version_attr)
            path = ConditionPath(path=[dynamo_name])
            version_condition = path == current_version

    final_condition = condition
    if version_condition is not None:
        final_condition = (
            final_condition & version_condition if final_condition else version_condition
        )

    table = model._get_table()
    key = model._get_key()

    op: dict[str, Any] = {"type": "delete", "table": table, "key": key}

    if final_condition is not None:
        names: dict[str, str] = {}
        values: dict[str, Any] = {}
        expr = final_condition.serialize(names, values)
        op["condition_expression"] = expr
        op["expression_attribute_names"] = {v: k for k, v in names.items()}
        op["expression_attribute_values"] = values

    txn._operations.append(op)


def _finalize_models(
    models: list[tuple[Model, str | None, int]],
) -> None:
    """Update version attributes and reset change tracking after successful commit."""
    for model, version_attr, new_version in models:
        if version_attr is not None:
            setattr(model, version_attr, new_version)
        model._reset_change_tracking()
