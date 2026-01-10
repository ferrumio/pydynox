"""Model base class with ORM-style CRUD operations."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, TypeVar

from pydynox._internal._model._async import (
    async_delete,
    async_delete_by_key,
    async_get,
    async_save,
    async_update,
    async_update_by_key,
)
from pydynox._internal._model._base import ModelBase, ModelMeta
from pydynox._internal._model._batch import batch_get
from pydynox._internal._model._crud import (
    delete,
    delete_by_key,
    get,
    save,
    update,
    update_by_key,
)
from pydynox._internal._model._query import (
    async_count,
    async_execute_statement,
    async_parallel_scan,
    async_query,
    async_scan,
    count,
    execute_statement,
    parallel_scan,
    query,
    scan,
)
from pydynox._internal._model._s3_helpers import (
    _async_delete_s3_files,
    _async_upload_s3_files,
    _delete_s3_files,
    _upload_s3_files,
)
from pydynox._internal._model._ttl import (
    _get_ttl_attr_name,
    expires_in,
    extend_ttl,
    is_expired,
)
from pydynox._internal._model._version import (
    _build_version_condition,
    _get_version_attr_name,
)
from pydynox._internal._results import (
    AsyncModelQueryResult,
    AsyncModelScanResult,
    ModelQueryResult,
    ModelScanResult,
)

if TYPE_CHECKING:
    from pydynox._internal._atomic import AtomicOp
    from pydynox._internal._metrics import OperationMetrics
    from pydynox.conditions import Condition

__all__ = [
    "Model",
    "ModelQueryResult",
    "AsyncModelQueryResult",
    "ModelScanResult",
    "AsyncModelScanResult",
]

M = TypeVar("M", bound="Model")


class Model(ModelBase, metaclass=ModelMeta):
    """Base class for DynamoDB models with ORM-style CRUD.

    Example:
        >>> from pydynox import Model, ModelConfig
        >>> from pydynox.attributes import StringAttribute
        >>>
        >>> class User(Model):
        ...     model_config = ModelConfig(table="users")
        ...     pk = StringAttribute(hash_key=True)
        ...     sk = StringAttribute(range_key=True)
        ...     name = StringAttribute()
        >>>
        >>> user = User(pk="USER#1", sk="PROFILE", name="John")
        >>> user.save()
    """

    # ========== SYNC CRUD ==========

    @classmethod
    def get(
        cls: type[M],
        consistent_read: bool | None = None,
        as_dict: bool = False,
        **keys: Any,
    ) -> M | dict[str, Any] | None:
        """Get an item from DynamoDB by its key.

        Args:
            consistent_read: Use strongly consistent read. Defaults to model_config value.
            as_dict: If True, return dict instead of Model instance.
            **keys: The key attributes (hash_key and optional range_key).

        Returns:
            The model instance (or dict if as_dict=True) if found, None otherwise.

        Example:
            >>> user = User.get(pk="USER#1", sk="PROFILE")
            >>> if user:
            ...     print(user.name)
            >>>
            >>> # Return as dict for better performance
            >>> user_dict = User.get(pk="USER#1", sk="PROFILE", as_dict=True)
        """
        return get(cls, consistent_read, as_dict, **keys)

    def save(self, condition: Condition | None = None, skip_hooks: bool | None = None) -> None:
        """Save the model to DynamoDB.

        Args:
            condition: Optional condition that must be true for the write.
            skip_hooks: If True, skip before/after save hooks.

        Raises:
            ConditionCheckFailedError: If the condition is not met.
            ItemTooLargeError: If item exceeds max_size in model_config.

        Example:
            >>> user = User(pk="USER#1", sk="PROFILE", name="John")
            >>> user.save()
            >>>
            >>> # With condition (prevent overwrite)
            >>> user.save(condition=User.pk.does_not_exist())
        """
        save(self, condition, skip_hooks)

    def delete(self, condition: Condition | None = None, skip_hooks: bool | None = None) -> None:
        """Delete the model from DynamoDB.

        Args:
            condition: Optional condition that must be true for the delete.
            skip_hooks: If True, skip before/after delete hooks.

        Raises:
            ConditionCheckFailedError: If the condition is not met.

        Example:
            >>> user = User.get(pk="USER#1", sk="PROFILE")
            >>> user.delete()
            >>>
            >>> # With condition
            >>> user.delete(condition=User.status == "inactive")
        """
        delete(self, condition, skip_hooks)

    def update(
        self,
        atomic: list[AtomicOp] | None = None,
        condition: Condition | None = None,
        skip_hooks: bool | None = None,
        **kwargs: Any,
    ) -> None:
        """Update specific attributes on the model.

        Args:
            atomic: List of atomic operations (SET, ADD, REMOVE, etc).
            condition: Optional condition that must be true for the update.
            skip_hooks: If True, skip before/after update hooks.
            **kwargs: Attribute names and new values to update.

        Example:
            >>> user = User.get(pk="USER#1", sk="PROFILE")
            >>>
            >>> # Simple update
            >>> user.update(name="Jane")
            >>>
            >>> # Atomic operations
            >>> from pydynox.atomic import AtomicOp
            >>> user.update(atomic=[AtomicOp.add("login_count", 1)])
        """
        update(self, atomic, condition, skip_hooks, **kwargs)

    @classmethod
    def update_by_key(cls: type[M], condition: Condition | None = None, **kwargs: Any) -> None:
        """Update an item by key without fetching it first.

        Args:
            condition: Optional condition that must be true for the update.
            **kwargs: Must include key attributes plus attributes to update.

        Example:
            >>> # Update without fetching
            >>> User.update_by_key(pk="USER#1", sk="PROFILE", name="Jane")
        """
        update_by_key(cls, condition, **kwargs)

    @classmethod
    def delete_by_key(cls: type[M], condition: Condition | None = None, **kwargs: Any) -> None:
        """Delete an item by key without fetching it first.

        Args:
            condition: Optional condition that must be true for the delete.
            **kwargs: The key attributes (hash_key and optional range_key).

        Example:
            >>> User.delete_by_key(pk="USER#1", sk="PROFILE")
        """
        delete_by_key(cls, condition, **kwargs)

    @classmethod
    def batch_get(
        cls: type[M],
        keys: list[dict[str, Any]],
        consistent_read: bool | None = None,
        as_dict: bool = False,
    ) -> list[M] | list[dict[str, Any]]:
        """Batch get multiple items by their keys.

        Args:
            keys: List of key dicts (each with hash_key and optional range_key).
            consistent_read: Use strongly consistent read.
            as_dict: If True, return dicts instead of Model instances.

        Returns:
            List of model instances or dicts.

        Example:
            >>> keys = [
            ...     {"pk": "USER#1", "sk": "PROFILE"},
            ...     {"pk": "USER#2", "sk": "PROFILE"},
            ... ]
            >>> users = User.batch_get(keys)
            >>> for user in users:
            ...     print(user.name)
            >>>
            >>> # Return as dicts for better performance
            >>> users = User.batch_get(keys, as_dict=True)
        """
        return batch_get(cls, keys, consistent_read, as_dict)

    # ========== ASYNC CRUD ==========

    @classmethod
    async def async_get(
        cls: type[M],
        consistent_read: bool | None = None,
        as_dict: bool = False,
        **keys: Any,
    ) -> M | dict[str, Any] | None:
        """Async version of get.

        Example:
            >>> user = await User.async_get(pk="USER#1", sk="PROFILE")
            >>>
            >>> # Return as dict for better performance
            >>> user_dict = await User.async_get(pk="USER#1", as_dict=True)
        """
        return await async_get(cls, consistent_read, as_dict, **keys)

    async def async_save(
        self, condition: Condition | None = None, skip_hooks: bool | None = None
    ) -> None:
        """Async version of save.

        Example:
            >>> user = User(pk="USER#1", sk="PROFILE", name="John")
            >>> await user.async_save()
        """
        await async_save(self, condition, skip_hooks)

    async def async_delete(
        self, condition: Condition | None = None, skip_hooks: bool | None = None
    ) -> None:
        """Async version of delete.

        Example:
            >>> user = await User.async_get(pk="USER#1", sk="PROFILE")
            >>> await user.async_delete()
        """
        await async_delete(self, condition, skip_hooks)

    async def async_update(
        self,
        atomic: list[AtomicOp] | None = None,
        condition: Condition | None = None,
        skip_hooks: bool | None = None,
        **kwargs: Any,
    ) -> None:
        """Async version of update.

        Example:
            >>> user = await User.async_get(pk="USER#1", sk="PROFILE")
            >>> await user.async_update(name="Jane")
        """
        await async_update(self, atomic, condition, skip_hooks, **kwargs)

    @classmethod
    async def async_update_by_key(
        cls: type[M], condition: Condition | None = None, **kwargs: Any
    ) -> None:
        """Async version of update_by_key.

        Example:
            >>> await User.async_update_by_key(pk="USER#1", sk="PROFILE", name="Jane")
        """
        await async_update_by_key(cls, condition, **kwargs)

    @classmethod
    async def async_delete_by_key(
        cls: type[M], condition: Condition | None = None, **kwargs: Any
    ) -> None:
        """Async version of delete_by_key.

        Example:
            >>> await User.async_delete_by_key(pk="USER#1", sk="PROFILE")
        """
        await async_delete_by_key(cls, condition, **kwargs)

    # ========== QUERY/SCAN ==========

    @classmethod
    def query(
        cls: type[M],
        hash_key: Any,
        range_key_condition: Condition | None = None,
        filter_condition: Condition | None = None,
        limit: int | None = None,
        scan_index_forward: bool = True,
        consistent_read: bool | None = None,
        last_evaluated_key: dict[str, Any] | None = None,
        as_dict: bool = False,
    ) -> ModelQueryResult[M]:
        """Query items by hash key with optional conditions.

        Args:
            hash_key: The hash key value to query.
            range_key_condition: Optional condition on range key.
            filter_condition: Optional filter applied after query.
            limit: Maximum items to return.
            scan_index_forward: True for ascending, False for descending.
            consistent_read: Use strongly consistent read.
            last_evaluated_key: Start key for pagination.
            as_dict: If True, return dicts instead of Model instances.

        Returns:
            Iterable result that auto-paginates.

        Example:
            >>> # Get all orders for a user
            >>> for order in Order.query(hash_key="USER#1"):
            ...     print(order.order_id)
            >>>
            >>> # With range key condition
            >>> recent = Order.query(
            ...     hash_key="USER#1",
            ...     range_key_condition=Order.sk.begins_with("ORDER#2024")
            ... )
            >>>
            >>> # Return as dicts for better performance
            >>> for order in Order.query(hash_key="USER#1", as_dict=True):
            ...     print(order["order_id"])
        """
        return query(
            cls,
            hash_key,
            range_key_condition,
            filter_condition,
            limit,
            scan_index_forward,
            consistent_read,
            last_evaluated_key,
            as_dict,
        )

    @classmethod
    def scan(
        cls: type[M],
        filter_condition: Condition | None = None,
        limit: int | None = None,
        consistent_read: bool | None = None,
        last_evaluated_key: dict[str, Any] | None = None,
        segment: int | None = None,
        total_segments: int | None = None,
        as_dict: bool = False,
    ) -> ModelScanResult[M]:
        """Scan all items in the table.

        Args:
            filter_condition: Optional filter applied after scan.
            limit: Maximum items to return.
            consistent_read: Use strongly consistent read.
            last_evaluated_key: Start key for pagination.
            segment: Segment number for parallel scan.
            total_segments: Total segments for parallel scan.
            as_dict: If True, return dicts instead of Model instances.

        Returns:
            Iterable result that auto-paginates.

        Example:
            >>> # Scan all users
            >>> for user in User.scan():
            ...     print(user.name)
            >>>
            >>> # With filter
            >>> active = User.scan(filter_condition=User.status == "active")
            >>>
            >>> # Return as dicts for better performance
            >>> for user in User.scan(as_dict=True):
            ...     print(user["name"])
        """
        return scan(
            cls,
            filter_condition,
            limit,
            consistent_read,
            last_evaluated_key,
            segment,
            total_segments,
            as_dict,
        )

    @classmethod
    def count(
        cls: type[M],
        filter_condition: Condition | None = None,
        consistent_read: bool | None = None,
    ) -> tuple[int, OperationMetrics]:
        """Count items in the table.

        Args:
            filter_condition: Optional filter to count matching items.
            consistent_read: Use strongly consistent read.

        Returns:
            Tuple of (count, metrics).

        Example:
            >>> total, metrics = User.count()
            >>> print(f"Total users: {total}")
            >>>
            >>> # Count with filter
            >>> active, _ = User.count(filter_condition=User.status == "active")
        """
        return count(cls, filter_condition, consistent_read)

    @classmethod
    def execute_statement(
        cls: type[M],
        statement: str,
        parameters: list[Any] | None = None,
        consistent_read: bool = False,
    ) -> list[M]:
        """Execute a PartiQL statement and return typed model instances.

        Args:
            statement: PartiQL SELECT statement.
            parameters: Optional parameters for the statement.
            consistent_read: Use strongly consistent read.

        Returns:
            List of model instances.

        Example:
            >>> users = User.execute_statement(
            ...     "SELECT * FROM users WHERE pk = ?",
            ...     parameters=["USER#1"]
            ... )
        """
        return execute_statement(cls, statement, parameters, consistent_read)

    @classmethod
    def async_query(
        cls: type[M],
        hash_key: Any,
        range_key_condition: Condition | None = None,
        filter_condition: Condition | None = None,
        limit: int | None = None,
        scan_index_forward: bool = True,
        consistent_read: bool | None = None,
        last_evaluated_key: dict[str, Any] | None = None,
        as_dict: bool = False,
    ) -> AsyncModelQueryResult[M]:
        """Async version of query.

        Example:
            >>> async for order in Order.async_query(hash_key="USER#1"):
            ...     print(order.order_id)
            >>>
            >>> # Return as dicts for better performance
            >>> async for order in Order.async_query(hash_key="USER#1", as_dict=True):
            ...     print(order["order_id"])
        """
        return async_query(
            cls,
            hash_key,
            range_key_condition,
            filter_condition,
            limit,
            scan_index_forward,
            consistent_read,
            last_evaluated_key,
            as_dict,
        )

    @classmethod
    def async_scan(
        cls: type[M],
        filter_condition: Condition | None = None,
        limit: int | None = None,
        consistent_read: bool | None = None,
        last_evaluated_key: dict[str, Any] | None = None,
        segment: int | None = None,
        total_segments: int | None = None,
        as_dict: bool = False,
    ) -> AsyncModelScanResult[M]:
        """Async version of scan.

        Example:
            >>> async for user in User.async_scan():
            ...     print(user.name)
            >>>
            >>> # Return as dicts for better performance
            >>> async for user in User.async_scan(as_dict=True):
            ...     print(user["name"])
        """
        return async_scan(
            cls,
            filter_condition,
            limit,
            consistent_read,
            last_evaluated_key,
            segment,
            total_segments,
            as_dict,
        )

    @classmethod
    async def async_count(
        cls: type[M],
        filter_condition: Condition | None = None,
        consistent_read: bool | None = None,
    ) -> tuple[int, OperationMetrics]:
        """Async version of count.

        Example:
            >>> total, metrics = await User.async_count()
        """
        return await async_count(cls, filter_condition, consistent_read)

    @classmethod
    async def async_execute_statement(
        cls: type[M],
        statement: str,
        parameters: list[Any] | None = None,
        consistent_read: bool = False,
    ) -> list[M]:
        """Async version of execute_statement.

        Example:
            >>> users = await User.async_execute_statement(
            ...     "SELECT * FROM users WHERE pk = ?",
            ...     parameters=["USER#1"]
            ... )
        """
        return await async_execute_statement(cls, statement, parameters, consistent_read)

    @classmethod
    def parallel_scan(
        cls: type[M],
        total_segments: int,
        filter_condition: Condition | None = None,
        consistent_read: bool | None = None,
        as_dict: bool = False,
    ) -> tuple[list[M] | list[dict[str, Any]], OperationMetrics]:
        """Parallel scan - runs multiple segment scans concurrently.

        Args:
            total_segments: Number of parallel segments (workers).
            filter_condition: Optional filter applied after scan.
            consistent_read: Use strongly consistent read.
            as_dict: If True, return dicts instead of Model instances.

        Returns:
            Tuple of (list of items, combined metrics).

        Example:
            >>> # Scan with 4 parallel workers
            >>> users, metrics = User.parallel_scan(total_segments=4)
            >>> print(f"Found {len(users)} users")
            >>>
            >>> # Return as dicts for better performance
            >>> users, metrics = User.parallel_scan(total_segments=4, as_dict=True)
        """
        return parallel_scan(cls, total_segments, filter_condition, consistent_read, as_dict)

    @classmethod
    async def async_parallel_scan(
        cls: type[M],
        total_segments: int,
        filter_condition: Condition | None = None,
        consistent_read: bool | None = None,
        as_dict: bool = False,
    ) -> tuple[list[M] | list[dict[str, Any]], OperationMetrics]:
        """Async parallel scan - runs multiple segment scans concurrently.

        Example:
            >>> users, metrics = await User.async_parallel_scan(total_segments=4)
            >>>
            >>> # Return as dicts for better performance
            >>> users, metrics = await User.async_parallel_scan(total_segments=4, as_dict=True)
        """
        return await async_parallel_scan(
            cls, total_segments, filter_condition, consistent_read, as_dict
        )

    # ========== TTL ==========

    def _get_ttl_attr_name(self) -> str | None:
        """Get the name of the TTL attribute if defined."""
        return _get_ttl_attr_name(self)

    @property
    def is_expired(self) -> bool:
        """Check if the TTL has passed.

        Returns:
            True if expired, False otherwise. Returns False if no TTL attribute.

        Example:
            >>> session = Session.get(pk="SESSION#1")
            >>> if session.is_expired:
            ...     print("Session expired")
        """
        return is_expired(self)

    @property
    def expires_in(self) -> timedelta | None:
        """Get time remaining until expiration.

        Returns:
            timedelta until expiration, or None if expired/no TTL.

        Example:
            >>> session = Session.get(pk="SESSION#1")
            >>> remaining = session.expires_in
            >>> if remaining:
            ...     print(f"Expires in {remaining.total_seconds()} seconds")
        """
        return expires_in(self)

    def extend_ttl(self, new_expiration: datetime) -> None:
        """Extend the TTL to a new expiration time.

        Args:
            new_expiration: New expiration datetime (must be timezone-aware).

        Raises:
            ValueError: If model has no TTL attribute.

        Example:
            >>> from datetime import datetime, timedelta, timezone
            >>> session = Session.get(pk="SESSION#1")
            >>> new_exp = datetime.now(timezone.utc) + timedelta(hours=1)
            >>> session.extend_ttl(new_exp)
            >>> session.save()
        """
        extend_ttl(self, new_expiration)

    # ========== VERSION ==========

    def _get_version_attr_name(self) -> str | None:
        """Get the name of the version attribute if defined."""
        return _get_version_attr_name(self)

    def _build_version_condition(self) -> tuple[Condition | None, int]:
        """Build condition for optimistic locking."""
        return _build_version_condition(self)

    # ========== S3 ==========

    def _upload_s3_files(self) -> None:
        """Upload S3File values to S3 and replace with S3Value."""
        _upload_s3_files(self)

    async def _async_upload_s3_files(self) -> None:
        """Async upload S3File values to S3 and replace with S3Value."""
        await _async_upload_s3_files(self)

    def _delete_s3_files(self) -> None:
        """Delete S3 files associated with this model."""
        _delete_s3_files(self)

    async def _async_delete_s3_files(self) -> None:
        """Async delete S3 files associated with this model."""
        await _async_delete_s3_files(self)

    # ========== TABLE OPERATIONS ==========

    @classmethod
    def create_table(
        cls,
        billing_mode: str = "PAY_PER_REQUEST",
        read_capacity: int | None = None,
        write_capacity: int | None = None,
        table_class: str | None = None,
        encryption: str | None = None,
        kms_key_id: str | None = None,
        wait: bool = False,
    ) -> None:
        """Create the DynamoDB table for this model.

        Uses the model's schema to build the table definition, including
        hash key, range key, and any GSIs defined on the model.

        Args:
            billing_mode: "PAY_PER_REQUEST" (default) or "PROVISIONED".
            read_capacity: Read capacity units (only for PROVISIONED).
            write_capacity: Write capacity units (only for PROVISIONED).
            table_class: "STANDARD" (default) or "STANDARD_INFREQUENT_ACCESS".
            encryption: "AWS_OWNED", "AWS_MANAGED", or "CUSTOMER_MANAGED".
            kms_key_id: KMS key ARN (required for CUSTOMER_MANAGED).
            wait: If True, wait for table to become active.

        Raises:
            ValueError: If model has no hash_key defined.
            TableAlreadyExistsError: If table already exists.

        Example:
            >>> class User(Model):
            ...     model_config = ModelConfig(table="users")
            ...     pk = StringAttribute(hash_key=True)
            ...     sk = StringAttribute(range_key=True)
            ...     email = StringAttribute()
            ...
            ...     email_index = GlobalSecondaryIndex(
            ...         index_name="email-index",
            ...         hash_key="email",
            ...     )
            >>>
            >>> User.create_table(wait=True)
        """
        if cls._hash_key is None:
            raise ValueError(f"Model {cls.__name__} has no hash_key defined")

        client = cls._get_client()
        table = cls._get_table()

        # Get hash key type
        hash_key_attr = cls._attributes[cls._hash_key]
        hash_key = (cls._hash_key, hash_key_attr.attr_type)

        # Get range key type if defined
        range_key = None
        if cls._range_key:
            range_key_attr = cls._attributes[cls._range_key]
            range_key = (cls._range_key, range_key_attr.attr_type)

        # Build GSI definitions
        gsis = None
        if cls._indexes:
            gsis = [idx.to_create_table_definition(cls) for idx in cls._indexes.values()]

        client.create_table(
            table,
            hash_key=hash_key,
            range_key=range_key,
            billing_mode=billing_mode,
            read_capacity=read_capacity,
            write_capacity=write_capacity,
            table_class=table_class,
            encryption=encryption,
            kms_key_id=kms_key_id,
            global_secondary_indexes=gsis,
            wait=wait,
        )

    @classmethod
    def table_exists(cls) -> bool:
        """Check if the table for this model exists.

        Returns:
            True if table exists, False otherwise.

        Example:
            >>> if not User.table_exists():
            ...     User.create_table(wait=True)
        """
        client = cls._get_client()
        table = cls._get_table()
        return client.table_exists(table)

    @classmethod
    def delete_table(cls) -> None:
        """Delete the table for this model.

        Warning:
            This permanently deletes the table and all its data.

        Example:
            >>> User.delete_table()
        """
        client = cls._get_client()
        table = cls._get_table()
        client.delete_table(table)
