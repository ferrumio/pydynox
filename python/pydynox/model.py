"""Model base class with ORM-style CRUD operations."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, ClassVar, TypeVar

from pydynox._internal._atomic import AtomicOp, serialize_atomic
from pydynox._internal._conditions import ConditionPath
from pydynox._internal._results import (
    AsyncModelQueryResult,
    AsyncModelScanResult,
    ModelQueryResult,
    ModelScanResult,
)
from pydynox._internal._s3 import S3File, S3Value
from pydynox.attributes import Attribute
from pydynox.attributes.s3 import S3Attribute
from pydynox.attributes.ttl import TTLAttribute
from pydynox.attributes.version import VersionAttribute
from pydynox.client import DynamoDBClient
from pydynox.config import ModelConfig, get_default_client
from pydynox.exceptions import ItemTooLargeError
from pydynox.generators import generate_value, is_auto_generate
from pydynox.hooks import HookType
from pydynox.indexes import GlobalSecondaryIndex
from pydynox.size import ItemSize, calculate_item_size

if TYPE_CHECKING:
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


class ModelMeta(type):
    """Metaclass that collects attributes and builds schema."""

    _attributes: dict[str, Attribute[Any]]
    _hash_key: str | None
    _range_key: str | None
    _hooks: dict[HookType, list[Any]]
    _indexes: dict[str, GlobalSecondaryIndex[Any]]

    def __new__(mcs, name: str, bases: tuple[type, ...], namespace: dict[str, Any]) -> ModelMeta:
        attributes: dict[str, Attribute[Any]] = {}
        hash_key: str | None = None
        range_key: str | None = None
        hooks: dict[HookType, list[Any]] = {hook_type: [] for hook_type in HookType}
        indexes: dict[str, GlobalSecondaryIndex[Any]] = {}

        for base in bases:
            if hasattr(base, "_attributes"):
                attributes.update(base._attributes)
            if hasattr(base, "_hash_key") and base._hash_key:
                hash_key = base._hash_key
            if hasattr(base, "_range_key") and base._range_key:
                range_key = base._range_key
            if hasattr(base, "_hooks"):
                for hook_type, hook_list in base._hooks.items():
                    hooks[hook_type].extend(hook_list)
            if hasattr(base, "_indexes"):
                indexes.update(base._indexes)

        for attr_name, attr_value in namespace.items():
            if isinstance(attr_value, Attribute):
                attr_value.attr_name = attr_name
                attributes[attr_name] = attr_value

                if attr_value.hash_key:
                    hash_key = attr_name
                if attr_value.range_key:
                    range_key = attr_name

            if callable(attr_value) and hasattr(attr_value, "_hook_type"):
                hooks[getattr(attr_value, "_hook_type")].append(attr_value)

            if isinstance(attr_value, GlobalSecondaryIndex):
                indexes[attr_name] = attr_value

        cls = super().__new__(mcs, name, bases, namespace)

        cls._attributes = attributes
        cls._hash_key = hash_key
        cls._range_key = range_key
        cls._hooks = hooks
        cls._indexes = indexes

        for idx in indexes.values():
            idx._bind_to_model(cls)

        return cls


class Model(metaclass=ModelMeta):
    """Base class for DynamoDB models with ORM-style CRUD.

    Example:
        >>> class User(Model):
        ...     model_config = ModelConfig(table="users")
        ...     pk = StringAttribute(hash_key=True)
        ...     sk = StringAttribute(range_key=True)
        ...     name = StringAttribute()
    """

    _attributes: ClassVar[dict[str, Attribute[Any]]]
    _hash_key: ClassVar[str | None]
    _range_key: ClassVar[str | None]
    _hooks: ClassVar[dict[HookType, list[Any]]]
    _indexes: ClassVar[dict[str, GlobalSecondaryIndex[Any]]]
    _client_instance: ClassVar[DynamoDBClient | None] = None

    model_config: ClassVar[ModelConfig]

    def __init__(self, **kwargs: Any):
        for attr_name, attr in self._attributes.items():
            if attr_name in kwargs:
                setattr(self, attr_name, kwargs[attr_name])
            elif attr.default is not None:
                if is_auto_generate(attr.default):
                    setattr(self, attr_name, None)
                else:
                    setattr(self, attr_name, attr.default)
            elif not attr.null:
                raise ValueError(f"Attribute '{attr_name}' is required")
            else:
                setattr(self, attr_name, None)

    def _apply_auto_generate(self) -> None:
        """Apply auto-generate strategies to None attributes."""
        for attr_name, attr in self._attributes.items():
            if attr.default is not None and is_auto_generate(attr.default):
                current_value = getattr(self, attr_name, None)
                if current_value is None:
                    generated = generate_value(attr.default)
                    setattr(self, attr_name, generated)

    @classmethod
    def _get_client(cls) -> DynamoDBClient:
        """Get the DynamoDB client for this model."""
        if cls._client_instance is not None:
            return cls._client_instance

        if hasattr(cls, "model_config") and cls.model_config.client is not None:
            cls._client_instance = cls.model_config.client
            return cls._client_instance

        default = get_default_client()
        if default is not None:
            cls._client_instance = default
            return cls._client_instance

        raise ValueError(
            f"No client configured for {cls.__name__}. "
            "Either pass client to ModelConfig or call pydynox.set_default_client()"
        )

    @classmethod
    def _get_table(cls) -> str:
        """Get the table name from model_config."""
        if not hasattr(cls, "model_config"):
            raise ValueError(f"Model {cls.__name__} must define model_config")
        return cls.model_config.table

    def _should_skip_hooks(self, skip_hooks: bool | None) -> bool:
        if skip_hooks is not None:
            return skip_hooks
        if hasattr(self, "model_config"):
            return self.model_config.skip_hooks
        return False

    def _run_hooks(self, hook_type: HookType) -> None:
        for hook in self._hooks.get(hook_type, []):
            hook(self)

    @classmethod
    def get(cls: type[M], consistent_read: bool | None = None, **keys: Any) -> M | None:
        """Get an item from DynamoDB by its key.

        Args:
            consistent_read: If True, use strongly consistent read.
            **keys: The key attributes.

        Returns:
            The model instance if found, None otherwise.
        """
        client = cls._get_client()
        table = cls._get_table()

        use_consistent = consistent_read
        if use_consistent is None:
            use_consistent = getattr(cls.model_config, "consistent_read", False)

        item = client.get_item(table, keys, consistent_read=use_consistent)
        if item is None:
            return None

        instance = cls.from_dict(item)
        skip = cls.model_config.skip_hooks if hasattr(cls, "model_config") else False
        if not skip:
            instance._run_hooks(HookType.AFTER_LOAD)
        return instance

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
    ) -> ModelQueryResult[M]:
        """Query items by hash key with optional conditions.

        Args:
            hash_key: The hash key value to query.
            range_key_condition: Optional condition on the range key.
            filter_condition: Optional filter on non-key attributes.
            limit: Max items per page.
            scan_index_forward: Sort order. True = ascending, False = descending.
            consistent_read: If True, use strongly consistent read.
            last_evaluated_key: Start key for pagination.

        Returns:
            ModelQueryResult that yields typed model instances.
        """
        return ModelQueryResult(
            model_class=cls,
            hash_key_value=hash_key,
            range_key_condition=range_key_condition,
            filter_condition=filter_condition,
            limit=limit,
            scan_index_forward=scan_index_forward,
            consistent_read=consistent_read,
            last_evaluated_key=last_evaluated_key,
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
    ) -> ModelScanResult[M]:
        """Scan all items in the table.

        Warning: Scan reads every item in the table. Use query() when possible.

        Args:
            filter_condition: Optional filter on attributes.
            limit: Max items per page.
            consistent_read: If True, use strongly consistent read.
            last_evaluated_key: Start key for pagination.
            segment: Segment number for parallel scan (0 to total_segments-1).
            total_segments: Total number of segments for parallel scan.

        Returns:
            ModelScanResult that yields typed model instances.

        Example:
            >>> for user in User.scan():
            ...     print(user.name)
            >>>
            >>> # With filter
            >>> for user in User.scan(filter_condition=User.age >= 18):
            ...     print(user.name)
        """
        return ModelScanResult(
            model_class=cls,
            filter_condition=filter_condition,
            limit=limit,
            consistent_read=consistent_read,
            last_evaluated_key=last_evaluated_key,
            segment=segment,
            total_segments=total_segments,
        )

    @classmethod
    def count(
        cls: type[M],
        filter_condition: Condition | None = None,
        consistent_read: bool | None = None,
    ) -> tuple[int, OperationMetrics]:
        """Count items in the table.

        Warning: Count scans the entire table. Use sparingly.

        Args:
            filter_condition: Optional filter on attributes.
            consistent_read: If True, use strongly consistent read.

        Returns:
            Tuple of (count, metrics).

        Example:
            >>> count, metrics = User.count()
            >>> print(f"Total users: {count}")
        """
        client = cls._get_client()
        table = cls._get_table()

        names: dict[str, str] = {}
        values: dict[str, Any] = {}

        filter_expr = None
        if filter_condition is not None:
            filter_expr = filter_condition.serialize(names, values)

        attr_names = {v: k for k, v in names.items()}

        use_consistent = consistent_read
        if use_consistent is None:
            use_consistent = getattr(cls.model_config, "consistent_read", False)

        return client.count(
            table,
            filter_expression=filter_expr,
            expression_attribute_names=attr_names if attr_names else None,
            expression_attribute_values=values if values else None,
            consistent_read=use_consistent,
        )

    @classmethod
    def execute_statement(
        cls: type[M],
        statement: str,
        parameters: list[Any] | None = None,
        consistent_read: bool = False,
    ) -> list[M]:
        """Execute a PartiQL statement and return typed model instances."""
        client = cls._get_client()
        result = client.execute_statement(
            statement,
            parameters=parameters,
            consistent_read=consistent_read,
        )
        return [cls.from_dict(item) for item in result]

    @classmethod
    async def async_execute_statement(
        cls: type[M],
        statement: str,
        parameters: list[Any] | None = None,
        consistent_read: bool = False,
    ) -> list[M]:
        """Async version of execute_statement."""
        client = cls._get_client()
        result = await client.async_execute_statement(
            statement,
            parameters=parameters,
            consistent_read=consistent_read,
        )
        return [cls.from_dict(item) for item in result]

    def save(self, condition: Condition | None = None, skip_hooks: bool | None = None) -> None:
        """Save the model to DynamoDB."""
        skip = self._should_skip_hooks(skip_hooks)

        if not skip:
            self._run_hooks(HookType.BEFORE_SAVE)

        self._apply_auto_generate()

        # Upload S3 files before serialization
        self._upload_s3_files()

        version_attr = self._get_version_attr_name()
        version_condition, new_version = self._build_version_condition()

        final_condition = condition
        if version_condition is not None:
            if final_condition is not None:
                final_condition = final_condition & version_condition
            else:
                final_condition = version_condition

        if version_attr is not None:
            setattr(self, version_attr, new_version)

        max_size = (
            getattr(self.model_config, "max_size", None) if hasattr(self, "model_config") else None
        )
        if max_size is not None:
            size = self.calculate_size()
            if size.bytes > max_size:
                raise ItemTooLargeError(
                    size=size.bytes,
                    max_size=max_size,
                    item_key=self._get_key(),
                )

        client = self._get_client()
        table = self._get_table()
        item = self.to_dict()

        if final_condition is not None:
            names: dict[str, str] = {}
            values: dict[str, Any] = {}
            expr = final_condition.serialize(names, values)
            attr_names = {v: k for k, v in names.items()}
            client.put_item(
                table,
                item,
                condition_expression=expr,
                expression_attribute_names=attr_names,
                expression_attribute_values=values,
            )
        else:
            client.put_item(table, item)

        if not skip:
            self._run_hooks(HookType.AFTER_SAVE)

    def delete(self, condition: Condition | None = None, skip_hooks: bool | None = None) -> None:
        """Delete the model from DynamoDB."""
        skip = self._should_skip_hooks(skip_hooks)

        if not skip:
            self._run_hooks(HookType.BEFORE_DELETE)

        version_attr = self._get_version_attr_name()
        version_condition: Condition | None = None
        if version_attr is not None:
            current_version: int | None = getattr(self, version_attr, None)
            if current_version is not None:
                path = ConditionPath(path=[version_attr])
                version_condition = path == current_version

        final_condition = condition
        if version_condition is not None:
            if final_condition is not None:
                final_condition = final_condition & version_condition
            else:
                final_condition = version_condition

        client = self._get_client()
        table = self._get_table()
        key = self._get_key()

        if final_condition is not None:
            names: dict[str, str] = {}
            values: dict[str, Any] = {}
            expr = final_condition.serialize(names, values)
            attr_names = {v: k for k, v in names.items()}
            client.delete_item(
                table,
                key,
                condition_expression=expr,
                expression_attribute_names=attr_names,
                expression_attribute_values=values,
            )
        else:
            client.delete_item(table, key)

        # Delete S3 files after DynamoDB delete succeeds
        self._delete_s3_files()

        if not skip:
            self._run_hooks(HookType.AFTER_DELETE)

    def update(
        self,
        atomic: list[AtomicOp] | None = None,
        condition: Condition | None = None,
        skip_hooks: bool | None = None,
        **kwargs: Any,
    ) -> None:
        """Update specific attributes on the model."""
        skip = self._should_skip_hooks(skip_hooks)

        if not skip:
            self._run_hooks(HookType.BEFORE_UPDATE)

        client = self._get_client()
        table = self._get_table()
        key = self._get_key()

        if atomic:
            update_expr, names, values = serialize_atomic(atomic)
            attr_names = {v: k for k, v in names.items()}

            cond_expr = None
            if condition is not None:
                cond_names: dict[str, str] = dict(names)
                cond_expr = condition.serialize(cond_names, values)
                cond_attr_names = {v: k for k, v in cond_names.items()}
                attr_names = {**attr_names, **cond_attr_names}

            client.update_item(
                table,
                key,
                update_expression=update_expr,
                condition_expression=cond_expr,
                expression_attribute_names=attr_names if attr_names else None,
                expression_attribute_values=values if values else None,
            )
        elif kwargs:
            for attr_name, value in kwargs.items():
                if attr_name not in self._attributes:
                    raise ValueError(f"Unknown attribute: {attr_name}")
                setattr(self, attr_name, value)

            if condition is not None:
                kwargs_cond_names: dict[str, str] = {}
                kwargs_cond_values: dict[str, Any] = {}
                cond_expr = condition.serialize(kwargs_cond_names, kwargs_cond_values)
                attr_names = {v: k for k, v in kwargs_cond_names.items()}
                client.update_item(
                    table,
                    key,
                    updates=kwargs,
                    condition_expression=cond_expr,
                    expression_attribute_names=attr_names,
                    expression_attribute_values=kwargs_cond_values,
                )
            else:
                client.update_item(table, key, updates=kwargs)

        if not skip:
            self._run_hooks(HookType.AFTER_UPDATE)

    def _get_key(self) -> dict[str, Any]:
        key = {}
        if self._hash_key:
            key[self._hash_key] = getattr(self, self._hash_key)
        if self._range_key:
            key[self._range_key] = getattr(self, self._range_key)
        return key

    def to_dict(self) -> dict[str, Any]:
        """Convert the model to a dict."""
        result = {}
        for attr_name, attr in self._attributes.items():
            value = getattr(self, attr_name, None)
            if value is not None:
                result[attr_name] = attr.serialize(value)
        return result

    def calculate_size(self, detailed: bool = False) -> ItemSize:
        """Calculate the size of this item in bytes."""
        item = self.to_dict()
        return calculate_item_size(item, detailed=detailed)

    @classmethod
    def from_dict(cls: type[M], data: dict[str, Any]) -> M:
        """Create a model instance from a dict."""
        deserialized = {}
        for attr_name, value in data.items():
            if attr_name in cls._attributes:
                deserialized[attr_name] = cls._attributes[attr_name].deserialize(value)
            else:
                deserialized[attr_name] = value
        return cls(**deserialized)

    def __repr__(self) -> str:
        attrs = ", ".join(f"{k}={v!r}" for k, v in self.to_dict().items())
        return f"{self.__class__.__name__}({attrs})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return self._get_key() == other._get_key()

    def _get_ttl_attr_name(self) -> str | None:
        for attr_name, attr in self._attributes.items():
            if isinstance(attr, TTLAttribute):
                return attr_name
        return None

    def _get_version_attr_name(self) -> str | None:
        for attr_name, attr in self._attributes.items():
            if isinstance(attr, VersionAttribute):
                return attr_name
        return None

    def _build_version_condition(self) -> tuple[Condition | None, int]:
        version_attr = self._get_version_attr_name()
        if version_attr is None:
            return None, 0

        current_version: int | None = getattr(self, version_attr, None)
        path = ConditionPath(path=[version_attr])

        if current_version is None:
            return path.does_not_exist(), 1
        else:
            return path == current_version, current_version + 1

    def _upload_s3_files(self) -> None:
        """Upload S3File values to S3 and replace with S3Value."""
        client = self._get_client()
        for attr_name, attr in self._attributes.items():
            if isinstance(attr, S3Attribute):
                value = getattr(self, attr_name, None)
                if isinstance(value, S3File):
                    s3_value = attr.upload_to_s3(value, self, client)
                    setattr(self, attr_name, s3_value)

    async def _async_upload_s3_files(self) -> None:
        """Async upload S3File values to S3 and replace with S3Value."""
        client = self._get_client()
        for attr_name, attr in self._attributes.items():
            if isinstance(attr, S3Attribute):
                value = getattr(self, attr_name, None)
                if isinstance(value, S3File):
                    s3_value = await attr.async_upload_to_s3(value, self, client)
                    setattr(self, attr_name, s3_value)

    def _delete_s3_files(self) -> None:
        """Delete S3 files associated with this model."""
        client = self._get_client()
        for attr_name, attr in self._attributes.items():
            if isinstance(attr, S3Attribute):
                value = getattr(self, attr_name, None)
                if isinstance(value, S3Value):
                    attr.delete_from_s3(value, client)

    async def _async_delete_s3_files(self) -> None:
        """Async delete S3 files associated with this model."""
        client = self._get_client()
        for attr_name, attr in self._attributes.items():
            if isinstance(attr, S3Attribute):
                value = getattr(self, attr_name, None)
                if isinstance(value, S3Value):
                    await attr.async_delete_from_s3(value, client)

    @property
    def is_expired(self) -> bool:
        """Check if the TTL has passed."""
        ttl_attr = self._get_ttl_attr_name()
        if ttl_attr is None:
            return False

        expires_at: datetime | None = getattr(self, ttl_attr, None)
        if expires_at is None:
            return False

        return bool(datetime.now(timezone.utc) > expires_at)

    @property
    def expires_in(self) -> timedelta | None:
        """Get time remaining until expiration."""
        ttl_attr = self._get_ttl_attr_name()
        if ttl_attr is None:
            return None

        expires_at: datetime | None = getattr(self, ttl_attr, None)
        if expires_at is None:
            return None

        remaining: timedelta = expires_at - datetime.now(timezone.utc)
        if remaining.total_seconds() < 0:
            return None

        return remaining

    def extend_ttl(self, new_expiration: datetime) -> None:
        """Extend the TTL to a new expiration time."""
        ttl_attr = self._get_ttl_attr_name()
        if ttl_attr is None:
            raise ValueError(f"Model {self.__class__.__name__} has no TTLAttribute")

        setattr(self, ttl_attr, new_expiration)

        client = self._get_client()
        table = self._get_table()
        key = self._get_key()
        client.update_item(table, key, updates={ttl_attr: new_expiration})

    # ========== ASYNC METHODS ==========

    @classmethod
    async def async_get(cls: type[M], consistent_read: bool | None = None, **keys: Any) -> M | None:
        """Async version of get."""
        client = cls._get_client()
        table = cls._get_table()

        use_consistent = consistent_read
        if use_consistent is None:
            use_consistent = getattr(cls.model_config, "consistent_read", False)

        item = await client.async_get_item(table, keys, consistent_read=use_consistent)
        if item is None:
            return None

        instance = cls.from_dict(item)
        skip = cls.model_config.skip_hooks if hasattr(cls, "model_config") else False
        if not skip:
            instance._run_hooks(HookType.AFTER_LOAD)
        return instance

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
    ) -> AsyncModelQueryResult[M]:
        """Async version of query."""
        return AsyncModelQueryResult(
            model_class=cls,
            hash_key_value=hash_key,
            range_key_condition=range_key_condition,
            filter_condition=filter_condition,
            limit=limit,
            scan_index_forward=scan_index_forward,
            consistent_read=consistent_read,
            last_evaluated_key=last_evaluated_key,
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
    ) -> AsyncModelScanResult[M]:
        """Async version of scan."""
        return AsyncModelScanResult(
            model_class=cls,
            filter_condition=filter_condition,
            limit=limit,
            consistent_read=consistent_read,
            last_evaluated_key=last_evaluated_key,
            segment=segment,
            total_segments=total_segments,
        )

    @classmethod
    async def async_count(
        cls: type[M],
        filter_condition: Condition | None = None,
        consistent_read: bool | None = None,
    ) -> tuple[int, OperationMetrics]:
        """Async version of count."""
        client = cls._get_client()
        table = cls._get_table()

        names: dict[str, str] = {}
        values: dict[str, Any] = {}

        filter_expr = None
        if filter_condition is not None:
            filter_expr = filter_condition.serialize(names, values)

        attr_names = {v: k for k, v in names.items()}

        use_consistent = consistent_read
        if use_consistent is None:
            use_consistent = getattr(cls.model_config, "consistent_read", False)

        result = await client.async_count(
            table,
            filter_expression=filter_expr,
            expression_attribute_names=attr_names if attr_names else None,
            expression_attribute_values=values if values else None,
            consistent_read=use_consistent,
        )
        return result

    async def async_save(
        self, condition: Condition | None = None, skip_hooks: bool | None = None
    ) -> None:
        """Async version of save."""
        skip = self._should_skip_hooks(skip_hooks)

        if not skip:
            self._run_hooks(HookType.BEFORE_SAVE)

        self._apply_auto_generate()

        # Upload S3 files before serialization
        await self._async_upload_s3_files()

        version_attr = self._get_version_attr_name()
        version_condition, new_version = self._build_version_condition()

        final_condition = condition
        if version_condition is not None:
            if final_condition is not None:
                final_condition = final_condition & version_condition
            else:
                final_condition = version_condition

        if version_attr is not None:
            setattr(self, version_attr, new_version)

        max_size = (
            getattr(self.model_config, "max_size", None) if hasattr(self, "model_config") else None
        )
        if max_size is not None:
            size = self.calculate_size()
            if size.bytes > max_size:
                raise ItemTooLargeError(
                    size=size.bytes,
                    max_size=max_size,
                    item_key=self._get_key(),
                )

        client = self._get_client()
        table = self._get_table()
        item = self.to_dict()

        if final_condition is not None:
            names: dict[str, str] = {}
            values: dict[str, Any] = {}
            expr = final_condition.serialize(names, values)
            attr_names = {v: k for k, v in names.items()}
            await client.async_put_item(
                table,
                item,
                condition_expression=expr,
                expression_attribute_names=attr_names,
                expression_attribute_values=values,
            )
        else:
            await client.async_put_item(table, item)

        if not skip:
            self._run_hooks(HookType.AFTER_SAVE)

    async def async_delete(
        self, condition: Condition | None = None, skip_hooks: bool | None = None
    ) -> None:
        """Async version of delete."""
        skip = self._should_skip_hooks(skip_hooks)

        if not skip:
            self._run_hooks(HookType.BEFORE_DELETE)

        version_attr = self._get_version_attr_name()
        version_condition: Condition | None = None
        if version_attr is not None:
            current_version: int | None = getattr(self, version_attr, None)
            if current_version is not None:
                path = ConditionPath(path=[version_attr])
                version_condition = path == current_version

        final_condition = condition
        if version_condition is not None:
            if final_condition is not None:
                final_condition = final_condition & version_condition
            else:
                final_condition = version_condition

        client = self._get_client()
        table = self._get_table()
        key = self._get_key()

        if final_condition is not None:
            names: dict[str, str] = {}
            values: dict[str, Any] = {}
            expr = final_condition.serialize(names, values)
            attr_names = {v: k for k, v in names.items()}
            await client.async_delete_item(
                table,
                key,
                condition_expression=expr,
                expression_attribute_names=attr_names,
                expression_attribute_values=values,
            )
        else:
            await client.async_delete_item(table, key)

        # Delete S3 files after DynamoDB delete succeeds
        await self._async_delete_s3_files()

        if not skip:
            self._run_hooks(HookType.AFTER_DELETE)

    async def async_update(
        self,
        atomic: list[AtomicOp] | None = None,
        condition: Condition | None = None,
        skip_hooks: bool | None = None,
        **kwargs: Any,
    ) -> None:
        """Async version of update."""
        skip = self._should_skip_hooks(skip_hooks)

        if not skip:
            self._run_hooks(HookType.BEFORE_UPDATE)

        client = self._get_client()
        table = self._get_table()
        key = self._get_key()

        if atomic:
            update_expr, names, values = serialize_atomic(atomic)
            attr_names = {v: k for k, v in names.items()}

            cond_expr = None
            if condition is not None:
                cond_names: dict[str, str] = dict(names)
                cond_expr = condition.serialize(cond_names, values)
                cond_attr_names = {v: k for k, v in cond_names.items()}
                attr_names = {**attr_names, **cond_attr_names}

            await client.async_update_item(
                table,
                key,
                update_expression=update_expr,
                condition_expression=cond_expr,
                expression_attribute_names=attr_names if attr_names else None,
                expression_attribute_values=values if values else None,
            )
        elif kwargs:
            for attr_name, value in kwargs.items():
                if attr_name not in self._attributes:
                    raise ValueError(f"Unknown attribute: {attr_name}")
                setattr(self, attr_name, value)

            if condition is not None:
                kwargs_cond_names: dict[str, str] = {}
                kwargs_cond_values: dict[str, Any] = {}
                cond_expr = condition.serialize(kwargs_cond_names, kwargs_cond_values)
                attr_names = {v: k for k, v in kwargs_cond_names.items()}
                await client.async_update_item(
                    table,
                    key,
                    updates=kwargs,
                    condition_expression=cond_expr,
                    expression_attribute_names=attr_names,
                    expression_attribute_values=kwargs_cond_values,
                )
            else:
                await client.async_update_item(table, key, updates=kwargs)

        if not skip:
            self._run_hooks(HookType.AFTER_UPDATE)

    # ========== STATIC KEY-BASED METHODS ==========

    @classmethod
    def _extract_key_from_kwargs(
        cls, kwargs: dict[str, Any]
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Split kwargs into key attributes and updates.

        Returns:
            Tuple of (key_dict, updates_dict).

        Raises:
            ValueError: If hash_key is missing or range_key is missing when required.
        """
        if cls._hash_key is None:
            raise ValueError(f"Model {cls.__name__} has no hash_key defined")

        key: dict[str, Any] = {}
        updates: dict[str, Any] = {}

        for attr_name, value in kwargs.items():
            if attr_name == cls._hash_key:
                key[attr_name] = value
            elif attr_name == cls._range_key:
                key[attr_name] = value
            else:
                updates[attr_name] = value

        if cls._hash_key not in key:
            raise ValueError(f"Missing required hash_key: {cls._hash_key}")

        if cls._range_key is not None and cls._range_key not in key:
            raise ValueError(f"Missing required range_key: {cls._range_key}")

        return key, updates

    @classmethod
    def update_by_key(
        cls: type[M],
        condition: Condition | None = None,
        **kwargs: Any,
    ) -> None:
        """Update an item by key without fetching it first.

        This is faster than get() + update() because it makes only one
        DynamoDB call instead of two.

        Note: This method does NOT run lifecycle hooks. If you need hooks,
        use the traditional get() + update() approach.

        Args:
            condition: Optional condition for the update.
            **kwargs: Must include hash_key (and range_key if defined).
                      Other kwargs are the attributes to update.

        Raises:
            ValueError: If hash_key or range_key is missing.
            ConditionCheckFailedError: If condition is not met.

        Example:
            >>> User.update_by_key(pk="USER#1", sk="PROFILE", name="Jane", age=31)
        """
        key, updates = cls._extract_key_from_kwargs(kwargs)

        if not updates:
            return  # Nothing to update

        for attr_name in updates:
            if attr_name not in cls._attributes:
                raise ValueError(f"Unknown attribute: {attr_name}")

        client = cls._get_client()
        table = cls._get_table()

        if condition is not None:
            names: dict[str, str] = {}
            values: dict[str, Any] = {}
            cond_expr = condition.serialize(names, values)
            attr_names = {v: k for k, v in names.items()}
            client.update_item(
                table,
                key,
                updates=updates,
                condition_expression=cond_expr,
                expression_attribute_names=attr_names if attr_names else None,
                expression_attribute_values=values if values else None,
            )
        else:
            client.update_item(table, key, updates=updates)

    @classmethod
    def delete_by_key(
        cls: type[M],
        condition: Condition | None = None,
        **kwargs: Any,
    ) -> None:
        """Delete an item by key without fetching it first.

        This is faster than get() + delete() because it makes only one
        DynamoDB call instead of two.

        Note: This method does NOT run lifecycle hooks. If you need hooks,
        use the traditional get() + delete() approach.

        Args:
            condition: Optional condition for the delete.
            **kwargs: Must include hash_key (and range_key if defined).

        Raises:
            ValueError: If hash_key or range_key is missing.
            ConditionCheckFailedError: If condition is not met.

        Example:
            >>> User.delete_by_key(pk="USER#1", sk="PROFILE")
        """
        key, _ = cls._extract_key_from_kwargs(kwargs)

        client = cls._get_client()
        table = cls._get_table()

        if condition is not None:
            names: dict[str, str] = {}
            values: dict[str, Any] = {}
            cond_expr = condition.serialize(names, values)
            attr_names = {v: k for k, v in names.items()}
            client.delete_item(
                table,
                key,
                condition_expression=cond_expr,
                expression_attribute_names=attr_names,
                expression_attribute_values=values,
            )
        else:
            client.delete_item(table, key)

    @classmethod
    async def async_update_by_key(
        cls: type[M],
        condition: Condition | None = None,
        **kwargs: Any,
    ) -> None:
        """Async version of update_by_key.

        Note: This method does NOT run lifecycle hooks.

        Args:
            condition: Optional condition for the update.
            **kwargs: Must include hash_key (and range_key if defined).
                      Other kwargs are the attributes to update.

        Example:
            >>> await User.async_update_by_key(pk="USER#1", sk="PROFILE", name="Jane")
        """
        key, updates = cls._extract_key_from_kwargs(kwargs)

        if not updates:
            return  # Nothing to update

        for attr_name in updates:
            if attr_name not in cls._attributes:
                raise ValueError(f"Unknown attribute: {attr_name}")

        client = cls._get_client()
        table = cls._get_table()

        if condition is not None:
            names: dict[str, str] = {}
            values: dict[str, Any] = {}
            cond_expr = condition.serialize(names, values)
            attr_names = {v: k for k, v in names.items()}
            await client.async_update_item(
                table,
                key,
                updates=updates,
                condition_expression=cond_expr,
                expression_attribute_names=attr_names if attr_names else None,
                expression_attribute_values=values if values else None,
            )
        else:
            await client.async_update_item(table, key, updates=updates)

    @classmethod
    async def async_delete_by_key(
        cls: type[M],
        condition: Condition | None = None,
        **kwargs: Any,
    ) -> None:
        """Async version of delete_by_key.

        Args:
            condition: Optional condition for the delete.
            **kwargs: Must include hash_key (and range_key if defined).

        Example:
            >>> await User.async_delete_by_key(pk="USER#1", sk="PROFILE")
        """
        key, _ = cls._extract_key_from_kwargs(kwargs)

        client = cls._get_client()
        table = cls._get_table()

        if condition is not None:
            names: dict[str, str] = {}
            values: dict[str, Any] = {}
            cond_expr = condition.serialize(names, values)
            attr_names = {v: k for k, v in names.items()}
            await client.async_delete_item(
                table,
                key,
                condition_expression=cond_expr,
                expression_attribute_names=attr_names,
                expression_attribute_values=values,
            )
        else:
            await client.async_delete_item(table, key)
