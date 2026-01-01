"""Model base class with ORM-style CRUD operations."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, ClassVar, TypeVar

from pydynox._internal._atomic import AtomicOp, serialize_atomic
from pydynox.attributes import Attribute, TTLAttribute
from pydynox.client import DynamoDBClient
from pydynox.config import ModelConfig, get_default_client
from pydynox.exceptions import ItemTooLargeError
from pydynox.hooks import HookType
from pydynox.indexes import GlobalSecondaryIndex
from pydynox.size import ItemSize, calculate_item_size

if TYPE_CHECKING:
    from pydynox.conditions import Condition

M = TypeVar("M", bound="Model")


class ModelMeta(type):
    """Metaclass that collects attributes and builds schema."""

    _attributes: dict[str, Attribute[Any]]
    _hash_key: str | None
    _range_key: str | None
    _hooks: dict[HookType, list[Any]]
    _indexes: dict[str, GlobalSecondaryIndex[Any]]

    def __new__(mcs, name: str, bases: tuple[type, ...], namespace: dict[str, Any]) -> ModelMeta:
        # Collect attributes from parent classes
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

        # Collect attributes, hooks, and indexes from this class
        for attr_name, attr_value in namespace.items():
            if isinstance(attr_value, Attribute):
                attr_value.attr_name = attr_name
                attributes[attr_name] = attr_value

                if attr_value.hash_key:
                    hash_key = attr_name
                if attr_value.range_key:
                    range_key = attr_name

            # Collect hooks
            if callable(attr_value) and hasattr(attr_value, "_hook_type"):
                hooks[getattr(attr_value, "_hook_type")].append(attr_value)

            # Collect GSIs
            if isinstance(attr_value, GlobalSecondaryIndex):
                indexes[attr_name] = attr_value

        # Create the class
        cls = super().__new__(mcs, name, bases, namespace)

        # Store metadata
        cls._attributes = attributes
        cls._hash_key = hash_key
        cls._range_key = range_key
        cls._hooks = hooks
        cls._indexes = indexes

        # Bind indexes to this model class
        for idx in indexes.values():
            idx._bind_to_model(cls)

        return cls


class Model(metaclass=ModelMeta):
    """Base class for DynamoDB models with ORM-style CRUD.

    Define your model by subclassing and adding attributes:

    Example:
        >>> from pydynox import DynamoDBClient, Model, ModelConfig, set_default_client
        >>> from pydynox.attributes import StringAttribute, NumberAttribute
        >>>
        >>> # Option 1: Set a default client for all models
        >>> client = DynamoDBClient(region="us-east-1")
        >>> set_default_client(client)
        >>>
        >>> class User(Model):
        ...     model_config = ModelConfig(table="users")
        ...     pk = StringAttribute(hash_key=True)
        ...     sk = StringAttribute(range_key=True)
        ...     name = StringAttribute()
        ...     age = NumberAttribute()
        >>>
        >>> # Option 2: Pass client to ModelConfig
        >>> class Order(Model):
        ...     model_config = ModelConfig(
        ...         table="orders",
        ...         client=DynamoDBClient(region="eu-west-1"),
        ...     )
        ...     pk = StringAttribute(hash_key=True)
        >>>
        >>> # Create and save
        >>> user = User(pk="USER#123", sk="PROFILE", name="John", age=30)
        >>> user.save()
        >>>
        >>> # Get by key
        >>> user = User.get(pk="USER#123", sk="PROFILE")
        >>> print(user.name)
        >>>
        >>> # Update
        >>> user.name = "Jane"
        >>> user.save()
        >>>
        >>> # Delete
        >>> user.delete()
    """

    _attributes: ClassVar[dict[str, Attribute[Any]]]
    _hash_key: ClassVar[str | None]
    _range_key: ClassVar[str | None]
    _hooks: ClassVar[dict[HookType, list[Any]]]
    _indexes: ClassVar[dict[str, GlobalSecondaryIndex[Any]]]
    _client_instance: ClassVar[DynamoDBClient | None] = None

    model_config: ClassVar[ModelConfig]

    def __init__(self, **kwargs: Any):
        """Create a model instance.

        Args:
            **kwargs: Attribute values.
        """
        for attr_name, attr in self._attributes.items():
            if attr_name in kwargs:
                setattr(self, attr_name, kwargs[attr_name])
            elif attr.default is not None:
                setattr(self, attr_name, attr.default)
            elif not attr.null:
                raise ValueError(f"Attribute '{attr_name}' is required")
            else:
                setattr(self, attr_name, None)

    @classmethod
    def _get_client(cls) -> DynamoDBClient:
        """Get the DynamoDB client for this model.

        Priority:
        1. Client from model_config.client
        2. Global default client (set via set_default_client)
        3. Error if neither is set
        """
        # Check if we have a cached client instance
        if cls._client_instance is not None:
            return cls._client_instance

        # Check model_config.client first
        if hasattr(cls, "model_config") and cls.model_config.client is not None:
            cls._client_instance = cls.model_config.client
            return cls._client_instance

        # Check global default
        default = get_default_client()
        if default is not None:
            cls._client_instance = default
            return cls._client_instance

        # No client configured
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
        """Check if hooks should be skipped."""
        if skip_hooks is not None:
            return skip_hooks
        if hasattr(self, "model_config"):
            return self.model_config.skip_hooks
        return False

    def _run_hooks(self, hook_type: HookType) -> None:
        """Run all hooks of the given type."""
        for hook in self._hooks.get(hook_type, []):
            hook(self)

    @classmethod
    def get(cls: type[M], **keys: Any) -> M | None:
        """Get an item from DynamoDB by its key.

        Args:
            **keys: The key attributes (hash_key and optional range_key).

        Returns:
            The model instance if found, None otherwise.

        Example:
            >>> user = User.get(pk="USER#123", sk="PROFILE")
            >>> if user:
            ...     print(user.name)
        """
        client = cls._get_client()
        table = cls._get_table()

        item = client.get_item(table, keys)
        if item is None:
            return None

        instance = cls.from_dict(item)
        skip = cls.model_config.skip_hooks if hasattr(cls, "model_config") else False
        if not skip:
            instance._run_hooks(HookType.AFTER_LOAD)
        return instance

    def save(self, condition: Condition | None = None, skip_hooks: bool | None = None) -> None:
        """Save the model to DynamoDB.

        Creates a new item or replaces an existing one.

        Args:
            condition: Optional condition that must be true for the write.
            skip_hooks: Skip hooks for this operation. If None, uses model_config.skip_hooks.

        Raises:
            ItemTooLargeError: If max_size is set and item exceeds it.
            ConditionCheckFailedError: If the condition is not met.

        Example:
            >>> user = User(pk="USER#123", sk="PROFILE", name="John")
            >>> user.save()

            >>> # Only save if item doesn't exist
            >>> user.save(condition=User.pk.does_not_exist())
        """
        skip = self._should_skip_hooks(skip_hooks)

        if not skip:
            self._run_hooks(HookType.BEFORE_SAVE)

        # Check size if max_size is set
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

        # Serialize condition if provided
        if condition is not None:
            names: dict[str, str] = {}
            values: dict[str, Any] = {}
            expr = condition.serialize(names, values)
            # Invert names dict for DynamoDB format
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
        """Delete the model from DynamoDB.

        Args:
            condition: Optional condition that must be true for the delete.
            skip_hooks: Skip hooks for this operation. If None, uses model_config.skip_hooks.

        Raises:
            ConditionCheckFailedError: If the condition is not met.

        Example:
            >>> user = User.get(pk="USER#123", sk="PROFILE")
            >>> user.delete()

            >>> # Only delete if version matches
            >>> user.delete(condition=User.version == 5)
        """
        skip = self._should_skip_hooks(skip_hooks)

        if not skip:
            self._run_hooks(HookType.BEFORE_DELETE)

        client = self._get_client()
        table = self._get_table()
        key = self._get_key()

        # Serialize condition if provided
        if condition is not None:
            names: dict[str, str] = {}
            values: dict[str, Any] = {}
            expr = condition.serialize(names, values)
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

        if not skip:
            self._run_hooks(HookType.AFTER_DELETE)

    def update(
        self,
        atomic: list[AtomicOp] | None = None,
        condition: Condition | None = None,
        skip_hooks: bool | None = None,
        **kwargs: Any,
    ) -> None:
        """Update specific attributes on the model.

        Updates both the local instance and DynamoDB.

        Args:
            atomic: List of atomic operations (add, append, remove, etc.).
            condition: Optional condition that must be true for the update.
            skip_hooks: Skip hooks for this operation. If None, uses model_config.skip_hooks.
            **kwargs: Attribute values to update (simple SET operations).

        Example:
            >>> user = User.get(pk="USER#123", sk="PROFILE")
            >>> user.update(name="Jane", age=31)

            >>> # Atomic operations
            >>> user.update(atomic=[User.login_count.add(1)])
            >>> user.update(atomic=[User.tags.append(["premium"])])

            >>> # Multiple atomic operations
            >>> user.update(atomic=[
            ...     User.login_count.add(1),
            ...     User.tags.append(["verified"]),
            ...     User.temp_token.remove(),
            ... ])

            >>> # With condition
            >>> user.update(
            ...     atomic=[User.balance.add(-100)],
            ...     condition=User.balance >= 100,
            ... )
        """
        skip = self._should_skip_hooks(skip_hooks)

        if not skip:
            self._run_hooks(HookType.BEFORE_UPDATE)

        client = self._get_client()
        table = self._get_table()
        key = self._get_key()

        # Handle atomic operations
        if atomic:
            update_expr, names, values = serialize_atomic(atomic)

            # Invert names dict for DynamoDB format: {placeholder: attr_name}
            attr_names = {v: k for k, v in names.items()}

            # Serialize condition if provided
            cond_expr = None
            if condition is not None:
                # Pass existing names/values to avoid placeholder collisions
                cond_names: dict[str, str] = dict(names)  # Copy existing names
                cond_expr = condition.serialize(cond_names, values)
                # Merge names (condition names also need inversion)
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
            # Simple key=value updates
            for attr_name, value in kwargs.items():
                if attr_name not in self._attributes:
                    raise ValueError(f"Unknown attribute: {attr_name}")
                setattr(self, attr_name, value)

            # Serialize condition if provided
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
        """Get the key dict for this instance."""
        key = {}
        if self._hash_key:
            key[self._hash_key] = getattr(self, self._hash_key)
        if self._range_key:
            key[self._range_key] = getattr(self, self._range_key)
        return key

    def to_dict(self) -> dict[str, Any]:
        """Convert the model to a dict.

        Returns:
            Dict with all attribute values.

        Example:
            >>> user = User(pk="USER#123", sk="PROFILE", name="John")
            >>> user.to_dict()
            {'pk': 'USER#123', 'sk': 'PROFILE', 'name': 'John'}
        """
        result = {}
        for attr_name, attr in self._attributes.items():
            value = getattr(self, attr_name, None)
            if value is not None:
                result[attr_name] = attr.serialize(value)
        return result

    def calculate_size(self, detailed: bool = False) -> ItemSize:
        """Calculate the size of this item in bytes.

        DynamoDB has a 400KB item size limit. Use this to check
        before saving.

        Args:
            detailed: If True, include per-field size breakdown.

        Returns:
            ItemSize with bytes, kb, percent, and is_over_limit.

        Example:
            >>> user = User(pk="USER#123", name="John", bio="..." * 10000)
            >>> size = user.calculate_size()
            >>> print(f"{size.bytes} bytes ({size.percent:.1f}% of limit)")
            >>>
            >>> # Get field breakdown
            >>> size = user.calculate_size(detailed=True)
            >>> for field, bytes in size.fields.items():
            ...     print(f"{field}: {bytes} bytes")
        """
        item = self.to_dict()
        return calculate_item_size(item, detailed=detailed)

    @classmethod
    def from_dict(cls: type[M], data: dict[str, Any]) -> M:
        """Create a model instance from a dict.

        Args:
            data: Dict with attribute values.

        Returns:
            A new model instance.

        Example:
            >>> data = {'pk': 'USER#123', 'sk': 'PROFILE', 'name': 'John'}
            >>> user = User.from_dict(data)
        """
        deserialized = {}
        for attr_name, value in data.items():
            if attr_name in cls._attributes:
                deserialized[attr_name] = cls._attributes[attr_name].deserialize(value)
            else:
                deserialized[attr_name] = value
        return cls(**deserialized)

    def __repr__(self) -> str:
        """Return a string representation of the model."""
        attrs = ", ".join(f"{k}={v!r}" for k, v in self.to_dict().items())
        return f"{self.__class__.__name__}({attrs})"

    def __eq__(self, other: object) -> bool:
        """Check equality based on key attributes."""
        if not isinstance(other, self.__class__):
            return False
        return self._get_key() == other._get_key()

    def _get_ttl_attr_name(self) -> str | None:
        """Find the TTLAttribute field name if one exists."""
        for attr_name, attr in self._attributes.items():
            if isinstance(attr, TTLAttribute):
                return attr_name
        return None

    @property
    def is_expired(self) -> bool:
        """Check if the TTL has passed.

        Returns:
            True if expired, False otherwise. Returns False if no TTL attribute.

        Example:
            >>> session = Session.get(pk="SESSION#123")
            >>> if session.is_expired:
            ...     print("Session expired")
        """
        ttl_attr = self._get_ttl_attr_name()
        if ttl_attr is None:
            return False

        expires_at: datetime | None = getattr(self, ttl_attr, None)
        if expires_at is None:
            return False

        return bool(datetime.now(timezone.utc) > expires_at)

    @property
    def expires_in(self) -> timedelta | None:
        """Get time remaining until expiration.

        Returns:
            timedelta until expiration, or None if no TTL or already expired.

        Example:
            >>> session = Session.get(pk="SESSION#123")
            >>> remaining = session.expires_in
            >>> if remaining:
            ...     print(f"Expires in {remaining.total_seconds()} seconds")
        """
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
        """Extend the TTL to a new expiration time.

        Updates both the local instance and DynamoDB.

        Args:
            new_expiration: New expiration datetime. Use ExpiresIn helper.

        Raises:
            ValueError: If model has no TTLAttribute.

        Example:
            >>> from pydynox.attributes import ExpiresIn
            >>> session = Session.get(pk="SESSION#123")
            >>> session.extend_ttl(ExpiresIn.hours(1))  # extend by 1 hour
        """
        ttl_attr = self._get_ttl_attr_name()
        if ttl_attr is None:
            raise ValueError(f"Model {self.__class__.__name__} has no TTLAttribute")

        # Update local instance
        setattr(self, ttl_attr, new_expiration)

        # Update in DynamoDB
        client = self._get_client()
        table = self._get_table()
        key = self._get_key()
        client.update_item(table, key, updates={ttl_attr: new_expiration})

    # ========== ASYNC METHODS ==========

    @classmethod
    async def async_get(cls: type[M], **keys: Any) -> M | None:
        """Async version of get.

        Args:
            **keys: The key attributes (hash_key and optional range_key).

        Returns:
            The model instance if found, None otherwise.

        Example:
            >>> user = await User.async_get(pk="USER#123", sk="PROFILE")
        """
        client = cls._get_client()
        table = cls._get_table()

        item = await client.async_get_item(table, keys)
        if item is None:
            return None

        instance = cls.from_dict(item)
        skip = cls.model_config.skip_hooks if hasattr(cls, "model_config") else False
        if not skip:
            instance._run_hooks(HookType.AFTER_LOAD)
        return instance

    async def async_save(
        self, condition: Condition | None = None, skip_hooks: bool | None = None
    ) -> None:
        """Async version of save.

        Args:
            condition: Optional condition that must be true for the write.
            skip_hooks: Skip hooks for this operation.

        Example:
            >>> user = User(pk="USER#123", sk="PROFILE", name="John")
            >>> await user.async_save()
        """
        skip = self._should_skip_hooks(skip_hooks)

        if not skip:
            self._run_hooks(HookType.BEFORE_SAVE)

        # Check size if max_size is set
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

        if condition is not None:
            names: dict[str, str] = {}
            values: dict[str, Any] = {}
            expr = condition.serialize(names, values)
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
        """Async version of delete.

        Args:
            condition: Optional condition that must be true for the delete.
            skip_hooks: Skip hooks for this operation.

        Example:
            >>> user = await User.async_get(pk="USER#123", sk="PROFILE")
            >>> await user.async_delete()
        """
        skip = self._should_skip_hooks(skip_hooks)

        if not skip:
            self._run_hooks(HookType.BEFORE_DELETE)

        client = self._get_client()
        table = self._get_table()
        key = self._get_key()

        if condition is not None:
            names: dict[str, str] = {}
            values: dict[str, Any] = {}
            expr = condition.serialize(names, values)
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

        if not skip:
            self._run_hooks(HookType.AFTER_DELETE)

    async def async_update(
        self,
        atomic: list[AtomicOp] | None = None,
        condition: Condition | None = None,
        skip_hooks: bool | None = None,
        **kwargs: Any,
    ) -> None:
        """Async version of update.

        Args:
            atomic: List of atomic operations.
            condition: Optional condition that must be true.
            skip_hooks: Skip hooks for this operation.
            **kwargs: Attribute values to update.

        Example:
            >>> user = await User.async_get(pk="USER#123", sk="PROFILE")
            >>> await user.async_update(name="Jane", age=31)
        """
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
