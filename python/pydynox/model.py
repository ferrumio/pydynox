"""Model base class with ORM-style CRUD operations."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, TypeVar

from pydynox._internal._model._async import (
    delete as async_delete,
)
from pydynox._internal._model._async import (
    delete_by_key as async_delete_by_key,
)
from pydynox._internal._model._async import (
    get as async_get,
)
from pydynox._internal._model._async import (
    save as async_save,
)
from pydynox._internal._model._async import (
    update as async_update,
)
from pydynox._internal._model._async import (
    update_by_key as async_update_by_key,
)
from pydynox._internal._model._base import ModelBase, ModelMeta
from pydynox._internal._model._batch import batch_get, sync_batch_get
from pydynox._internal._model._crud import (
    delete as sync_delete,
)
from pydynox._internal._model._crud import (
    delete_by_key as sync_delete_by_key,
)
from pydynox._internal._model._crud import (
    get as sync_get,
)
from pydynox._internal._model._crud import (
    save as sync_save,
)
from pydynox._internal._model._crud import (
    update as sync_update,
)
from pydynox._internal._model._crud import (
    update_by_key as sync_update_by_key,
)
from pydynox._internal._model._query import (
    count as async_count,
)
from pydynox._internal._model._query import (
    execute_statement as async_execute_statement,
)
from pydynox._internal._model._query import (
    parallel_scan as async_parallel_scan,
)
from pydynox._internal._model._query import (
    query as async_query,
)
from pydynox._internal._model._query import (
    scan as async_scan,
)
from pydynox._internal._model._query import (
    sync_count,
    sync_execute_statement,
    sync_parallel_scan,
    sync_query,
    sync_scan,
)
from pydynox._internal._model._s3_helpers import (
    _delete_s3_files,
    _sync_delete_s3_files,
    _sync_upload_s3_files,
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
    from pydynox._internal._metrics import ModelMetrics, OperationMetrics
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
        ...     pk = StringAttribute(partition_key=True)
        ...     sk = StringAttribute(sort_key=True)
        ...     name = StringAttribute()
        >>>
        >>> user = User(pk="USER#1", sk="PROFILE", name="John")
        >>> user.save()
    """

    # ========== SYNC CRUD ==========

    @classmethod
    def sync_get(
        cls: type[M],
        consistent_read: bool | None = None,
        as_dict: bool = False,
        **keys: Any,
    ) -> M | dict[str, Any] | None:
        """Get an item from DynamoDB by its key (sync).

        Args:
            consistent_read: Use strongly consistent read. Defaults to model_config value.
            as_dict: If True, return dict instead of Model instance.
            **keys: The key attributes (partition_key and optional sort_key).

        Returns:
            The model instance (or dict if as_dict=True) if found, None otherwise.

        Example:
            >>> user = User.sync_get(pk="USER#1", sk="PROFILE")
            >>> if user:
            ...     print(user.name)
        """
        return sync_get(cls, consistent_read, as_dict, **keys)

    def sync_save(self, condition: Condition | None = None, skip_hooks: bool | None = None) -> None:
        """Save the model to DynamoDB (sync).

        Args:
            condition: Optional condition that must be true for the write.
            skip_hooks: If True, skip before/after save hooks.

        Raises:
            ConditionalCheckFailedException: If the condition is not met.
            ItemTooLargeException: If item exceeds max_size in model_config.

        Example:
            >>> user = User(pk="USER#1", sk="PROFILE", name="John")
            >>> user.sync_save()
        """
        sync_save(self, condition, skip_hooks)

    def sync_delete(
        self, condition: Condition | None = None, skip_hooks: bool | None = None
    ) -> None:
        """Delete the model from DynamoDB (sync).

        Args:
            condition: Optional condition that must be true for the delete.
            skip_hooks: If True, skip before/after delete hooks.

        Raises:
            ConditionalCheckFailedException: If the condition is not met.

        Example:
            >>> user = User.sync_get(pk="USER#1", sk="PROFILE")
            >>> user.sync_delete()
        """
        sync_delete(self, condition, skip_hooks)

    def sync_update(
        self,
        atomic: list[AtomicOp] | None = None,
        condition: Condition | None = None,
        skip_hooks: bool | None = None,
        **kwargs: Any,
    ) -> None:
        """Update specific attributes on the model (sync).

        Args:
            atomic: List of atomic operations (SET, ADD, REMOVE, etc).
            condition: Optional condition that must be true for the update.
            skip_hooks: If True, skip before/after update hooks.
            **kwargs: Attribute names and new values to update.

        Example:
            >>> user = User.sync_get(pk="USER#1", sk="PROFILE")
            >>> user.sync_update(name="Jane")
        """
        sync_update(self, atomic, condition, skip_hooks, **kwargs)

    @classmethod
    def sync_update_by_key(cls: type[M], condition: Condition | None = None, **kwargs: Any) -> None:
        """Update an item by key without fetching it first (sync).

        Args:
            condition: Optional condition that must be true for the update.
            **kwargs: Must include key attributes plus attributes to update.

        Example:
            >>> User.sync_update_by_key(pk="USER#1", sk="PROFILE", name="Jane")
        """
        sync_update_by_key(cls, condition, **kwargs)

    @classmethod
    def sync_delete_by_key(cls: type[M], condition: Condition | None = None, **kwargs: Any) -> None:
        """Delete an item by key without fetching it first (sync).

        Args:
            condition: Optional condition that must be true for the delete.
            **kwargs: The key attributes (partition_key and optional sort_key).

        Example:
            >>> User.sync_delete_by_key(pk="USER#1", sk="PROFILE")
        """
        sync_delete_by_key(cls, condition, **kwargs)

    @classmethod
    def sync_batch_get(
        cls: type[M],
        keys: list[dict[str, Any]],
        consistent_read: bool | None = None,
        as_dict: bool = False,
    ) -> list[M] | list[dict[str, Any]]:
        """Sync batch get multiple items by their keys.

        Args:
            keys: List of key dicts (each with partition_key and optional sort_key).
            consistent_read: Use strongly consistent read.
            as_dict: If True, return dicts instead of Model instances.

        Returns:
            List of model instances or dicts.

        Example:
            >>> keys = [
            ...     {"pk": "USER#1", "sk": "PROFILE"},
            ...     {"pk": "USER#2", "sk": "PROFILE"},
            ... ]
            >>> users = User.sync_batch_get(keys)
            >>> for user in users:
            ...     print(user.name)
            >>>
            >>> # Return as dicts for better performance
            >>> users = User.sync_batch_get(keys, as_dict=True)
        """
        return sync_batch_get(cls, keys, consistent_read, as_dict)

    @classmethod
    async def batch_get(
        cls: type[M],
        keys: list[dict[str, Any]],
        consistent_read: bool | None = None,
        as_dict: bool = False,
    ) -> list[M] | list[dict[str, Any]]:
        """Async batch get multiple items by their keys (default).

        Args:
            keys: List of key dicts (each with partition_key and optional sort_key).
            consistent_read: Use strongly consistent read.
            as_dict: If True, return dicts instead of Model instances.

        Returns:
            List of model instances or dicts.

        Example:
            >>> keys = [
            ...     {"pk": "USER#1", "sk": "PROFILE"},
            ...     {"pk": "USER#2", "sk": "PROFILE"},
            ... ]
            >>> users = await User.batch_get(keys)
            >>> for user in users:
            ...     print(user.name)
        """
        return await batch_get(cls, keys, consistent_read, as_dict)

    # ========== ASYNC CRUD (default) ==========

    @classmethod
    async def get(
        cls: type[M],
        consistent_read: bool | None = None,
        as_dict: bool = False,
        **keys: Any,
    ) -> M | dict[str, Any] | None:
        """Get an item from DynamoDB by its key (async, default).

        Args:
            consistent_read: Use strongly consistent read. Defaults to model_config value.
            as_dict: If True, return dict instead of Model instance.
            **keys: The key attributes (partition_key and optional sort_key).

        Returns:
            The model instance (or dict if as_dict=True) if found, None otherwise.

        Example:
            >>> user = await User.get(pk="USER#1", sk="PROFILE")
            >>> if user:
            ...     print(user.name)
        """
        return await async_get(cls, consistent_read, as_dict, **keys)

    async def save(
        self, condition: Condition | None = None, skip_hooks: bool | None = None
    ) -> None:
        """Save the model to DynamoDB (async, default).

        Args:
            condition: Optional condition that must be true for the write.
            skip_hooks: If True, skip before/after save hooks.

        Raises:
            ConditionalCheckFailedException: If the condition is not met.
            ItemTooLargeException: If item exceeds max_size in model_config.

        Example:
            >>> user = User(pk="USER#1", sk="PROFILE", name="John")
            >>> await user.save()
        """
        await async_save(self, condition, skip_hooks)

    async def delete(
        self, condition: Condition | None = None, skip_hooks: bool | None = None
    ) -> None:
        """Delete the model from DynamoDB (async, default).

        Args:
            condition: Optional condition that must be true for the delete.
            skip_hooks: If True, skip before/after delete hooks.

        Raises:
            ConditionalCheckFailedException: If the condition is not met.

        Example:
            >>> user = await User.get(pk="USER#1", sk="PROFILE")
            >>> await user.delete()
        """
        await async_delete(self, condition, skip_hooks)

    async def update(
        self,
        atomic: list[AtomicOp] | None = None,
        condition: Condition | None = None,
        skip_hooks: bool | None = None,
        **kwargs: Any,
    ) -> None:
        """Update specific attributes on the model (async, default).

        Args:
            atomic: List of atomic operations (SET, ADD, REMOVE, etc).
            condition: Optional condition that must be true for the update.
            skip_hooks: If True, skip before/after update hooks.
            **kwargs: Attribute names and new values to update.

        Example:
            >>> user = await User.get(pk="USER#1", sk="PROFILE")
            >>> await user.update(name="Jane")
        """
        await async_update(self, atomic, condition, skip_hooks, **kwargs)

    @classmethod
    async def update_by_key(
        cls: type[M], condition: Condition | None = None, **kwargs: Any
    ) -> None:
        """Update an item by key without fetching it first (async, default).

        Args:
            condition: Optional condition that must be true for the update.
            **kwargs: Must include key attributes plus attributes to update.

        Example:
            >>> await User.update_by_key(pk="USER#1", sk="PROFILE", name="Jane")
        """
        await async_update_by_key(cls, condition, **kwargs)

    @classmethod
    async def delete_by_key(
        cls: type[M], condition: Condition | None = None, **kwargs: Any
    ) -> None:
        """Delete an item by key without fetching it first (async, default).

        Args:
            condition: Optional condition that must be true for the delete.
            **kwargs: The key attributes (partition_key and optional sort_key).

        Example:
            >>> await User.delete_by_key(pk="USER#1", sk="PROFILE")
        """
        await async_delete_by_key(cls, condition, **kwargs)

    # ========== SYNC QUERY/SCAN ==========

    @classmethod
    def sync_query(
        cls: type[M],
        partition_key: Any = None,
        sort_key_condition: Condition | None = None,
        filter_condition: Condition | None = None,
        limit: int | None = None,
        page_size: int | None = None,
        scan_index_forward: bool = True,
        consistent_read: bool | None = None,
        last_evaluated_key: dict[str, Any] | None = None,
        as_dict: bool = False,
        fields: list[str] | None = None,
        **kwargs: Any,
    ) -> ModelQueryResult[M]:
        """Query items by hash key with optional conditions (sync).

        Args:
            partition_key: The hash key value to query. Can be omitted if using template.
            sort_key_condition: Optional condition on range key.
            filter_condition: Optional filter applied after query.
            limit: Max total items to return across all pages.
            page_size: Items per page (passed as Limit to DynamoDB).
            scan_index_forward: True for ascending, False for descending.
            consistent_read: Use strongly consistent read.
            last_evaluated_key: Start key for pagination.
            as_dict: If True, return dicts instead of Model instances.
            fields: List of fields to return. Saves RCU.
            **kwargs: Template placeholder values (e.g., user_id="123").

        Returns:
            Iterable result that auto-paginates.

        Example:
            >>> # Direct hash key
            >>> for order in Order.sync_query(partition_key="USER#1"):
            ...     print(order.order_id)
            >>>
            >>> # Using template (if pk has template="USER#{user_id}")
            >>> for order in Order.sync_query(user_id="1"):
            ...     print(order.order_id)
        """
        return sync_query(
            cls,
            partition_key=partition_key,
            sort_key_condition=sort_key_condition,
            filter_condition=filter_condition,
            limit=limit,
            page_size=page_size,
            scan_index_forward=scan_index_forward,
            consistent_read=consistent_read,
            last_evaluated_key=last_evaluated_key,
            as_dict=as_dict,
            fields=fields,
            **kwargs,
        )

    @classmethod
    def sync_scan(
        cls: type[M],
        filter_condition: Condition | None = None,
        limit: int | None = None,
        page_size: int | None = None,
        consistent_read: bool | None = None,
        last_evaluated_key: dict[str, Any] | None = None,
        segment: int | None = None,
        total_segments: int | None = None,
        as_dict: bool = False,
        fields: list[str] | None = None,
    ) -> ModelScanResult[M]:
        """Scan all items in the table (sync).

        Args:
            filter_condition: Optional filter applied after scan.
            limit: Max total items to return across all pages.
            page_size: Items per page (passed as Limit to DynamoDB).
            consistent_read: Use strongly consistent read.
            last_evaluated_key: Start key for pagination.
            segment: Segment number for parallel scan.
            total_segments: Total segments for parallel scan.
            as_dict: If True, return dicts instead of Model instances.
            fields: List of fields to return. Saves RCU.

        Returns:
            Iterable result that auto-paginates.

        Example:
            >>> for user in User.sync_scan():
            ...     print(user.name)
        """
        return sync_scan(
            cls,
            filter_condition=filter_condition,
            limit=limit,
            page_size=page_size,
            consistent_read=consistent_read,
            last_evaluated_key=last_evaluated_key,
            segment=segment,
            total_segments=total_segments,
            as_dict=as_dict,
            fields=fields,
        )

    @classmethod
    def sync_count(
        cls: type[M],
        filter_condition: Condition | None = None,
        consistent_read: bool | None = None,
    ) -> tuple[int, OperationMetrics]:
        """Count items in the table (sync).

        Args:
            filter_condition: Optional filter to count matching items.
            consistent_read: Use strongly consistent read.

        Returns:
            Tuple of (count, metrics).

        Example:
            >>> total, metrics = User.sync_count()
            >>> print(f"Total users: {total}")
        """
        return sync_count(cls, filter_condition, consistent_read)

    @classmethod
    def sync_execute_statement(
        cls: type[M],
        statement: str,
        parameters: list[Any] | None = None,
        consistent_read: bool = False,
    ) -> list[M]:
        """Execute a PartiQL statement (sync).

        Args:
            statement: PartiQL SELECT statement.
            parameters: Optional parameters for the statement.
            consistent_read: Use strongly consistent read.

        Returns:
            List of model instances.

        Example:
            >>> users = User.sync_execute_statement(
            ...     "SELECT * FROM users WHERE pk = ?",
            ...     parameters=["USER#1"]
            ... )
        """
        return sync_execute_statement(cls, statement, parameters, consistent_read)

    @classmethod
    def sync_parallel_scan(
        cls: type[M],
        total_segments: int,
        filter_condition: Condition | None = None,
        consistent_read: bool | None = None,
        as_dict: bool = False,
    ) -> tuple[list[M] | list[dict[str, Any]], OperationMetrics]:
        """Parallel scan - runs multiple segment scans concurrently (sync).

        Args:
            total_segments: Number of parallel segments (workers).
            filter_condition: Optional filter applied after scan.
            consistent_read: Use strongly consistent read.
            as_dict: If True, return dicts instead of Model instances.

        Returns:
            Tuple of (list of items, combined metrics).

        Example:
            >>> users, metrics = User.sync_parallel_scan(total_segments=4)
            >>> print(f"Found {len(users)} users")
        """
        return sync_parallel_scan(cls, total_segments, filter_condition, consistent_read, as_dict)

    # ========== ASYNC QUERY/SCAN (default) ==========

    @classmethod
    def query(
        cls: type[M],
        partition_key: Any = None,
        sort_key_condition: Condition | None = None,
        filter_condition: Condition | None = None,
        limit: int | None = None,
        page_size: int | None = None,
        scan_index_forward: bool = True,
        consistent_read: bool | None = None,
        last_evaluated_key: dict[str, Any] | None = None,
        as_dict: bool = False,
        fields: list[str] | None = None,
        **kwargs: Any,
    ) -> AsyncModelQueryResult[M]:
        """Query items by hash key with optional conditions (async, default).

        Args:
            partition_key: The hash key value to query. Can be omitted if using template.
            sort_key_condition: Optional condition on range key.
            filter_condition: Optional filter applied after query.
            limit: Max total items to return across all pages.
            page_size: Items per page (passed as Limit to DynamoDB).
            scan_index_forward: True for ascending, False for descending.
            consistent_read: Use strongly consistent read.
            last_evaluated_key: Start key for pagination.
            as_dict: If True, return dicts instead of Model instances.
            fields: List of fields to return. Saves RCU.
            **kwargs: Template placeholder values (e.g., user_id="123").

        Returns:
            Async iterable result that auto-paginates.

        Example:
            >>> # Direct hash key
            >>> async for order in Order.query(partition_key="USER#1"):
            ...     print(order.order_id)
            >>>
            >>> # Using template (if pk has template="USER#{user_id}")
            >>> async for order in Order.query(user_id="1"):
            ...     print(order.order_id)
        """
        return async_query(
            cls,
            partition_key=partition_key,
            sort_key_condition=sort_key_condition,
            filter_condition=filter_condition,
            limit=limit,
            page_size=page_size,
            scan_index_forward=scan_index_forward,
            consistent_read=consistent_read,
            last_evaluated_key=last_evaluated_key,
            as_dict=as_dict,
            fields=fields,
            **kwargs,
        )

    @classmethod
    def scan(
        cls: type[M],
        filter_condition: Condition | None = None,
        limit: int | None = None,
        page_size: int | None = None,
        consistent_read: bool | None = None,
        last_evaluated_key: dict[str, Any] | None = None,
        segment: int | None = None,
        total_segments: int | None = None,
        as_dict: bool = False,
        fields: list[str] | None = None,
    ) -> AsyncModelScanResult[M]:
        """Scan all items in the table (async, default).

        Args:
            filter_condition: Optional filter applied after scan.
            limit: Max total items to return across all pages.
            page_size: Items per page (passed as Limit to DynamoDB).
            consistent_read: Use strongly consistent read.
            last_evaluated_key: Start key for pagination.
            segment: Segment number for parallel scan.
            total_segments: Total segments for parallel scan.
            as_dict: If True, return dicts instead of Model instances.
            fields: List of fields to return. Saves RCU.

        Returns:
            Async iterable result that auto-paginates.

        Example:
            >>> async for user in User.scan():
            ...     print(user.name)
        """
        return async_scan(
            cls,
            filter_condition=filter_condition,
            limit=limit,
            page_size=page_size,
            consistent_read=consistent_read,
            last_evaluated_key=last_evaluated_key,
            segment=segment,
            total_segments=total_segments,
            as_dict=as_dict,
            fields=fields,
        )

    @classmethod
    async def count(
        cls: type[M],
        filter_condition: Condition | None = None,
        consistent_read: bool | None = None,
    ) -> tuple[int, OperationMetrics]:
        """Count items in the table (async, default).

        Args:
            filter_condition: Optional filter to count matching items.
            consistent_read: Use strongly consistent read.

        Returns:
            Tuple of (count, metrics).

        Example:
            >>> total, metrics = await User.count()
            >>> print(f"Total users: {total}")
        """
        return await async_count(cls, filter_condition, consistent_read)

    @classmethod
    async def execute_statement(
        cls: type[M],
        statement: str,
        parameters: list[Any] | None = None,
        consistent_read: bool = False,
    ) -> list[M]:
        """Execute a PartiQL statement (async, default).

        Args:
            statement: PartiQL SELECT statement.
            parameters: Optional parameters for the statement.
            consistent_read: Use strongly consistent read.

        Returns:
            List of model instances.

        Example:
            >>> users = await User.execute_statement(
            ...     "SELECT * FROM users WHERE pk = ?",
            ...     parameters=["USER#1"]
            ... )
        """
        return await async_execute_statement(cls, statement, parameters, consistent_read)

    @classmethod
    async def parallel_scan(
        cls: type[M],
        total_segments: int,
        filter_condition: Condition | None = None,
        consistent_read: bool | None = None,
        as_dict: bool = False,
    ) -> tuple[list[M] | list[dict[str, Any]], OperationMetrics]:
        """Parallel scan - runs multiple segment scans concurrently (async, default).

        Args:
            total_segments: Number of parallel segments (workers).
            filter_condition: Optional filter applied after scan.
            consistent_read: Use strongly consistent read.
            as_dict: If True, return dicts instead of Model instances.

        Returns:
            Tuple of (list of items, combined metrics).

        Example:
            >>> users, metrics = await User.parallel_scan(total_segments=4)
            >>> print(f"Found {len(users)} users")
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

    # ========== S3 (ASYNC - default, no prefix) ==========

    async def _upload_s3_files(self) -> None:
        """Async upload S3File values to S3 and replace with S3Value."""
        await _upload_s3_files(self)

    async def _delete_s3_files(self) -> None:
        """Async delete S3 files associated with this model."""
        await _delete_s3_files(self)

    # ========== S3 (SYNC - with sync_ prefix) ==========

    def _sync_upload_s3_files(self) -> None:
        """Sync upload S3File values to S3 and replace with S3Value."""
        _sync_upload_s3_files(self)

    def _sync_delete_s3_files(self) -> None:
        """Sync delete S3 files associated with this model."""
        _sync_delete_s3_files(self)

    # ========== TABLE OPERATIONS (ASYNC - default, no prefix) ==========

    @classmethod
    async def create_table(
        cls,
        billing_mode: str = "PAY_PER_REQUEST",
        read_capacity: int | None = None,
        write_capacity: int | None = None,
        table_class: str | None = None,
        encryption: str | None = None,
        kms_key_id: str | None = None,
        wait: bool = False,
    ) -> None:
        """Create the DynamoDB table for this model. Async.

        Uses the model's schema to build the table definition, including
        hash key, range key, GSIs, and LSIs defined on the model.

        Args:
            billing_mode: "PAY_PER_REQUEST" (default) or "PROVISIONED".
            read_capacity: Read capacity units (only for PROVISIONED).
            write_capacity: Write capacity units (only for PROVISIONED).
            table_class: "STANDARD" (default) or "STANDARD_INFREQUENT_ACCESS".
            encryption: "AWS_OWNED", "AWS_MANAGED", or "CUSTOMER_MANAGED".
            kms_key_id: KMS key ARN (required for CUSTOMER_MANAGED).
            wait: If True, wait for table to become active.

        Raises:
            ValueError: If model has no partition_key defined.
            ResourceInUseException: If table already exists.

        Example:
            >>> await User.create_table(wait=True)
        """
        if cls._partition_key is None:
            raise ValueError(f"Model {cls.__name__} has no partition_key defined")

        client = cls._get_client()
        table = cls._get_table()

        # Get hash key type
        partition_key_attr = cls._attributes[cls._partition_key]
        partition_key = (cls._partition_key, partition_key_attr.attr_type)

        # Get range key type if defined
        sort_key = None
        if cls._sort_key:
            sort_key_attr = cls._attributes[cls._sort_key]
            sort_key = (cls._sort_key, sort_key_attr.attr_type)

        # Build GSI definitions
        gsis = None
        if cls._indexes:
            gsis = [idx.to_create_table_definition(cls) for idx in cls._indexes.values()]

        # Build LSI definitions
        lsis = None
        if cls._local_indexes:
            lsis = [idx.to_create_table_definition(cls) for idx in cls._local_indexes.values()]

        await client.create_table(
            table,
            partition_key=partition_key,
            sort_key=sort_key,
            billing_mode=billing_mode,
            read_capacity=read_capacity,
            write_capacity=write_capacity,
            table_class=table_class,
            encryption=encryption,
            kms_key_id=kms_key_id,
            global_secondary_indexes=gsis,
            local_secondary_indexes=lsis,
            wait=wait,
        )

    @classmethod
    async def table_exists(cls) -> bool:
        """Check if the table for this model exists. Async.

        Returns:
            True if table exists, False otherwise.

        Example:
            >>> if not await User.table_exists():
            ...     await User.create_table(wait=True)
        """
        client = cls._get_client()
        table = cls._get_table()
        return await client.table_exists(table)

    @classmethod
    async def delete_table(cls) -> None:
        """Delete the table for this model. Async.

        Warning:
            This permanently deletes the table and all its data.

        Example:
            >>> await User.delete_table()
        """
        client = cls._get_client()
        table = cls._get_table()
        await client.delete_table(table)

    # ========== TABLE OPERATIONS (SYNC - with sync_ prefix) ==========

    @classmethod
    def sync_create_table(
        cls,
        billing_mode: str = "PAY_PER_REQUEST",
        read_capacity: int | None = None,
        write_capacity: int | None = None,
        table_class: str | None = None,
        encryption: str | None = None,
        kms_key_id: str | None = None,
        wait: bool = False,
    ) -> None:
        """Create the DynamoDB table for this model. Sync (blocks).

        Uses the model's schema to build the table definition, including
        hash key, range key, GSIs, and LSIs defined on the model.

        Args:
            billing_mode: "PAY_PER_REQUEST" (default) or "PROVISIONED".
            read_capacity: Read capacity units (only for PROVISIONED).
            write_capacity: Write capacity units (only for PROVISIONED).
            table_class: "STANDARD" (default) or "STANDARD_INFREQUENT_ACCESS".
            encryption: "AWS_OWNED", "AWS_MANAGED", or "CUSTOMER_MANAGED".
            kms_key_id: KMS key ARN (required for CUSTOMER_MANAGED).
            wait: If True, wait for table to become active.

        Raises:
            ValueError: If model has no partition_key defined.
            ResourceInUseException: If table already exists.

        Example:
            >>> User.sync_create_table(wait=True)
        """
        if cls._partition_key is None:
            raise ValueError(f"Model {cls.__name__} has no partition_key defined")

        client = cls._get_client()
        table = cls._get_table()

        # Get hash key type
        partition_key_attr = cls._attributes[cls._partition_key]
        partition_key = (cls._partition_key, partition_key_attr.attr_type)

        # Get range key type if defined
        sort_key = None
        if cls._sort_key:
            sort_key_attr = cls._attributes[cls._sort_key]
            sort_key = (cls._sort_key, sort_key_attr.attr_type)

        # Build GSI definitions
        gsis = None
        if cls._indexes:
            gsis = [idx.to_create_table_definition(cls) for idx in cls._indexes.values()]

        # Build LSI definitions
        lsis = None
        if cls._local_indexes:
            lsis = [idx.to_create_table_definition(cls) for idx in cls._local_indexes.values()]

        client.sync_create_table(
            table,
            partition_key=partition_key,
            sort_key=sort_key,
            billing_mode=billing_mode,
            read_capacity=read_capacity,
            write_capacity=write_capacity,
            table_class=table_class,
            encryption=encryption,
            kms_key_id=kms_key_id,
            global_secondary_indexes=gsis,
            local_secondary_indexes=lsis,
            wait=wait,
        )

    @classmethod
    def sync_table_exists(cls) -> bool:
        """Check if the table for this model exists. Sync (blocks).

        Returns:
            True if table exists, False otherwise.

        Example:
            >>> if not User.sync_table_exists():
            ...     User.sync_create_table(wait=True)
        """
        client = cls._get_client()
        table = cls._get_table()
        return client.sync_table_exists(table)

    @classmethod
    def sync_delete_table(cls) -> None:
        """Delete the table for this model. Sync (blocks).

        Warning:
            This permanently deletes the table and all its data.

        Example:
            >>> User.sync_delete_table()
        """
        client = cls._get_client()
        table = cls._get_table()
        client.sync_delete_table(table)

    # ========== METRICS ==========

    @classmethod
    def get_last_metrics(cls) -> "OperationMetrics | None":
        """Get metrics from the last operation on this Model.

        Returns:
            OperationMetrics from the last operation, or None if no operations yet.

        Example:
            >>> user = User.get(pk="USER#1")
            >>> metrics = User.get_last_metrics()
            >>> if metrics:
            ...     print(f"RCU: {metrics.consumed_rcu}")
        """
        return cls._metrics_storage.last

    @classmethod
    def get_total_metrics(cls) -> "ModelMetrics":
        """Get aggregated metrics for all operations on this Model.

        Returns:
            ModelMetrics with totals for RCU, WCU, duration, and operation counts.

        Example:
            >>> # After several operations
            >>> metrics = User.get_total_metrics()
            >>> print(f"Total RCU: {metrics.total_rcu}")
            >>> print(f"Total WCU: {metrics.total_wcu}")
            >>> print(f"Operations: {metrics.operation_count}")
        """
        return cls._metrics_storage.total

    @classmethod
    def reset_metrics(cls) -> None:
        """Reset all metrics for this Model.

        Use this in long-running processes (FastAPI, Flask) to reset per request.
        Metrics accumulate forever if not reset.

        Example:
            >>> # At the start of each request
            >>> User.reset_metrics()
            >>> Order.reset_metrics()
            >>>
            >>> # ... do operations ...
            >>>
            >>> # At the end, check metrics
            >>> print(User.get_total_metrics())
        """
        cls._metrics_storage.reset()

    @classmethod
    def _record_metrics(cls, metrics: "OperationMetrics", operation: str) -> None:
        """Record metrics from an operation. Internal use only."""
        cls._metrics_storage.record(metrics, operation)
