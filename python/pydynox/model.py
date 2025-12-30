"""Model base class with ORM-style CRUD operations."""

from datetime import datetime, timedelta, timezone
from typing import Any, ClassVar, Optional, Type, TypeVar

from .attributes import Attribute, TTLAttribute
from .client import DynamoDBClient
from .config import ModelConfig, get_default_client
from .exceptions import ItemTooLargeError
from .hooks import HookType
from .size import ItemSize, calculate_item_size

M = TypeVar("M", bound="Model")


class ModelMeta(type):
    """Metaclass that collects attributes and builds schema."""

    def __new__(mcs, name: str, bases: tuple[type, ...], namespace: dict[str, Any]) -> "ModelMeta":
        # Collect attributes from parent classes
        attributes: dict[str, Attribute] = {}
        hash_key: Optional[str] = None
        range_key: Optional[str] = None
        hooks: dict[HookType, list] = {hook_type: [] for hook_type in HookType}

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

        # Collect attributes and hooks from this class
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
                hooks[attr_value._hook_type].append(attr_value)

        # Create the class
        cls = super().__new__(mcs, name, bases, namespace)

        # Store metadata
        cls._attributes = attributes
        cls._hash_key = hash_key
        cls._range_key = range_key
        cls._hooks = hooks

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

    _attributes: ClassVar[dict[str, Attribute]]
    _hash_key: ClassVar[Optional[str]]
    _range_key: ClassVar[Optional[str]]
    _hooks: ClassVar[dict[HookType, list]]
    _client_instance: ClassVar[Optional[DynamoDBClient]] = None

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

    def _should_skip_hooks(self, skip_hooks: Optional[bool]) -> bool:
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
    def get(cls: Type[M], **keys: Any) -> Optional[M]:
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

    def save(self, condition: Optional[str] = None, skip_hooks: Optional[bool] = None) -> None:
        """Save the model to DynamoDB.

        Creates a new item or replaces an existing one.

        Args:
            condition: Optional condition expression.
            skip_hooks: Skip hooks for this operation. If None, uses model_config.skip_hooks.

        Raises:
            ItemTooLargeError: If max_size is set and item exceeds it.

        Example:
            >>> user = User(pk="USER#123", sk="PROFILE", name="John")
            >>> user.save()
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

        # TODO: Add condition expression support when put_item supports it
        client.put_item(table, item)

        if not skip:
            self._run_hooks(HookType.AFTER_SAVE)

    def delete(self, condition: Optional[str] = None, skip_hooks: Optional[bool] = None) -> None:
        """Delete the model from DynamoDB.

        Args:
            condition: Optional condition expression.
            skip_hooks: Skip hooks for this operation. If None, uses model_config.skip_hooks.

        Example:
            >>> user = User.get(pk="USER#123", sk="PROFILE")
            >>> user.delete()
        """
        skip = self._should_skip_hooks(skip_hooks)

        if not skip:
            self._run_hooks(HookType.BEFORE_DELETE)

        client = self._get_client()
        table = self._get_table()
        key = self._get_key()

        # TODO: Add condition expression support
        client.delete_item(table, key)

        if not skip:
            self._run_hooks(HookType.AFTER_DELETE)

    def update(self, skip_hooks: Optional[bool] = None, **kwargs: Any) -> None:
        """Update specific attributes on the model.

        Updates both the local instance and DynamoDB.

        Args:
            skip_hooks: Skip hooks for this operation. If None, uses model_config.skip_hooks.
            **kwargs: Attribute values to update.

        Example:
            >>> user = User.get(pk="USER#123", sk="PROFILE")
            >>> user.update(name="Jane", age=31)
        """
        skip = self._should_skip_hooks(skip_hooks)

        if not skip:
            self._run_hooks(HookType.BEFORE_UPDATE)

        client = self._get_client()
        table = self._get_table()
        key = self._get_key()

        # Update local instance
        for attr_name, value in kwargs.items():
            if attr_name not in self._attributes:
                raise ValueError(f"Unknown attribute: {attr_name}")
            setattr(self, attr_name, value)

        # Update in DynamoDB
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
    def from_dict(cls: Type[M], data: dict[str, Any]) -> M:
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

    def _get_ttl_attr_name(self) -> Optional[str]:
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

        expires_at = getattr(self, ttl_attr, None)
        if expires_at is None:
            return False

        return datetime.now(timezone.utc) > expires_at

    @property
    def expires_in(self) -> Optional[timedelta]:
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

        expires_at = getattr(self, ttl_attr, None)
        if expires_at is None:
            return None

        remaining = expires_at - datetime.now(timezone.utc)
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

        self.update(**{ttl_attr: new_expiration})
